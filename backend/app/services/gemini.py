import asyncio
import base64
import json
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.config import settings
from app.formatting import classify_escape, escape_latex_in_json, format_tutor_message
from app.prompts import (
    CONTEXT_FILTER_AGENT_PROMPT,
    DRAW_AGENT_PROMPT,
    ROUTER_AGENT_PROMPT,
    TUTOR_AGENT_PROMPT,
    VISION_AGENT_PROMPT,
    VISION_PATCH_PROMPT,
)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    QUESTION = "question"
    CLARIFICATION = "clarification"
    ACKNOWLEDGMENT = "acknowledgment"
    CORRECTION = "correction"


@dataclass
class ConversationMessage:
    role: str                                   # "user" | "assistant"
    content: str
    message_type: MessageType | None = None     # only for user messages
    clarification_target: str | None = None     # e.g. "angle_B"
    had_screenshot: bool = False                # did this message include a board screenshot
    board_context: dict[str, Any] | None = None # board JSON at time of message (optional, for reference)


@dataclass
class RouterResult:
    needs_board: bool
    message_type: MessageType
    clarification_target: str | None
    reasoning: str


@dataclass
class PipelineResult:
    reply: str
    board_context: dict[str, Any] | None       # None if board was not analyzed
    todraw: dict[str, Any] | None              # None when tutor does not want to draw
    router: RouterResult
    message: ConversationMessage               # enriched user message ready to append to history


class AIServiceError(Exception):
    def __init__(
        self,
        message: str,
        service: str,
        model: str | None = None,
        original_exc: BaseException | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.service = service
        self.model = model
        self.original_exc = original_exc

    def __str__(self) -> str:
        if self.model:
            return f"[{self.service} ({self.model})] {self.message}"
        return f"[{self.service}] {self.message}"


def _normalize_todraw(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, str):
        trimmed = value.strip().lower()
        if trimmed in {"", "null", "none", "n/a", "na"}:
            return None
        return {"summary": value.strip(), "items": []}
    if isinstance(value, dict):
        items = value.get("items")
        if isinstance(items, list):
            if len(items) == 0:
                return None
            return value
        if items is None and not value.get("summary"):
            return None
        return value
    return None


def _salvage_message(raw: str) -> str:
    """Best-effort message extraction from JSON that failed to parse (truncated, bad escapes, ...)."""
    extractor = StreamingJsonStringExtractor("message")
    extractor.feed(raw)
    return extractor.accumulated if extractor.accumulated.strip() else raw


def _parse_tutor_response(raw: str) -> tuple[str, dict[str, Any] | None]:
    fallback = "I could not generate a reply."
    parsed = _parse_json_from_model(raw)
    if parsed.get("_parseError"):
        return (format_tutor_message(_salvage_message(raw)) or fallback), None
    message = parsed.get("message")
    if not isinstance(message, str) or not message.strip():
        # Model returned JSON but not in expected shape — fall back to raw text
        return (format_tutor_message(raw) or fallback), None
    return format_tutor_message(message) or fallback, _normalize_todraw(parsed.get("todraw"))


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------

_client: genai.Client | None = None
_client_key: str | None = None


def _get_client(agent_name: str, model_name: str) -> genai.Client:
    global _client, _client_key
    if not settings.gemini_api_key:
        raise AIServiceError("GEMINI_NOT_CONFIGURED", service=agent_name, model=model_name)
    if _client is None or _client_key != settings.gemini_api_key:
        _client = genai.Client(api_key=settings.gemini_api_key)
        _client_key = settings.gemini_api_key
    return _client


def _status_code(exc: BaseException) -> int | None:
    if isinstance(exc, genai_errors.APIError):
        return exc.code
    return None


def _is_transient_503(exc: BaseException) -> bool:
    if _status_code(exc) == 503:
        return True
    msg = str(exc).lower()
    return "503" in msg and ("high demand" in msg or "unavailable" in msg or "overloaded" in msg)


def _is_rate_limit(exc: BaseException) -> bool:
    if _status_code(exc) == 429:
        return True
    return "429" in str(exc) and "Too Many Requests" in str(exc)


def _to_service_error(exc: BaseException, agent_name: str, model_name: str) -> AIServiceError:
    if _is_rate_limit(exc):
        message = "Quota / rate limit exceeded (HTTP 429). Wait a minute and try again."
    elif _is_transient_503(exc):
        message = "Temporary service overload (HTTP 503). Try again in a minute."
    else:
        message = str(exc)
    return AIServiceError(message, service=agent_name, model=model_name, original_exc=exc)


def _backoff_seconds(attempt: int) -> float:
    """Exponential backoff for transient errors: 1.5s, 3s, 6s, ..."""
    return 1.5 * (2**attempt)


def _parse_json_from_model(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, flags=re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            parsed = json.loads(escape_latex_in_json(cleaned))
        except json.JSONDecodeError:
            return {"raw": cleaned, "_parseError": True}
    if isinstance(parsed, dict):
        return parsed
    return {"data": parsed}


def _is_gemma_model(model_name: str) -> bool:
    return model_name.lower().startswith("gemma")


def _build_request(
    *,
    model_name: str,
    system_instruction: str,
    parts: list[str | dict[str, bytes | str]],
) -> tuple[list[str | genai_types.Part], genai_types.GenerateContentConfig | None]:
    """Convert our simple part format (str | {mime_type, data}) to google-genai contents + config."""
    contents: list[str | genai_types.Part] = []

    # Gemma on Google AI Studio rejects system_instruction / developer role —
    # prepend the prompt as the first user turn instead.
    if _is_gemma_model(model_name):
        contents.append(system_instruction)
        config = None
    else:
        config = genai_types.GenerateContentConfig(system_instruction=system_instruction)

    for part in parts:
        if isinstance(part, str):
            contents.append(part)
        else:
            contents.append(
                genai_types.Part.from_bytes(data=part["data"], mime_type=part["mime_type"])  # type: ignore[arg-type]
            )
    return contents, config


async def _generate_content(
    *,
    model_name: str,
    system_instruction: str,
    parts: list[str | dict[str, bytes | str]],
    agent_name: str = "AI Assistant",
) -> str:
    client = _get_client(agent_name, model_name)
    contents, config = _build_request(
        model_name=model_name, system_instruction=system_instruction, parts=parts
    )

    max_attempts = max(1, settings.gemini_max_attempts)
    for attempt in range(max_attempts):
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            return (response.text or "").strip()
        except Exception as exc:
            # Only transient overloads are retried; quota errors and bad requests fail fast.
            if _is_transient_503(exc) and attempt < max_attempts - 1:
                await asyncio.sleep(_backoff_seconds(attempt))
                continue
            raise _to_service_error(exc, agent_name, model_name) from exc

    raise AIServiceError(  # pragma: no cover - loop always returns or raises
        "Failed after retries", service=agent_name, model=model_name
    )


class StreamingJsonStringExtractor:
    """
    Extracts the string content of a target key (default: 'message') from streaming JSON text,
    decoding escape sequences on the fly while strictly preserving LaTeX backslashes (\\int, \\frac, ...).
    If no JSON structure is detected, it falls back to emitting plain text.
    """

    def __init__(self, target_key: str = "message"):
        self.target_key = target_key
        self.raw = ""
        self.target_found = False
        self.completed = False
        self.accumulated = ""
        self.emitted_idx = 0
        self.is_plain_text = False

    def feed(self, chunk: str) -> str:
        if self.completed:
            return ""
        self.raw += chunk

        if not self.target_found and not self.is_plain_text:
            cleaned = self.raw.lstrip()
            fence_match = re.match(r"^```(?:json)?\s*", cleaned)
            search_text = cleaned[fence_match.end():] if fence_match else cleaned

            pattern = rf'"{self.target_key}"\s*:\s*"'
            match = re.search(pattern, search_text)
            if match:
                self.target_found = True
                content_after = search_text[match.end():]
                self._parse_string_content(content_after)
            else:
                stripped = search_text.strip()
                if len(stripped) > 80 and not stripped.startswith("{") and not stripped.startswith("```"):
                    self.is_plain_text = True
                    self.accumulated = self.raw
        elif self.target_found:
            cleaned = self.raw.lstrip()
            fence_match = re.match(r"^```(?:json)?\s*", cleaned)
            search_text = cleaned[fence_match.end():] if fence_match else cleaned

            pattern = rf'"{self.target_key}"\s*:\s*"'
            match = re.search(pattern, search_text)
            if match:
                content_after = search_text[match.end():]
                self._parse_string_content(content_after)
        elif self.is_plain_text:
            self.accumulated = self.raw

        delta = self.accumulated[self.emitted_idx:]
        self.emitted_idx = len(self.accumulated)
        return delta

    def _parse_string_content(self, text: str) -> None:
        result: list[str] = []
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == "\\":
                if i + 1 >= n:
                    # Lone trailing backslash at boundary — wait for next chunk
                    break
                next_c = text[i + 1]
                if next_c == '"':
                    result.append('"')
                    i += 2
                elif next_c == "\\":
                    result.append("\\")
                    i += 2
                elif next_c in ("n", "t", "r", "f", "b"):
                    kind = classify_escape(text, i, final=self.completed)
                    if kind == "latex":
                        result.append("\\")
                        result.append(next_c)
                        i += 2
                    elif kind == "wait":
                        break
                    else:
                        json_char = {
                            "n": "\n",
                            "t": "\t",
                            "r": "\r",
                            "f": "\f",
                            "b": "\b",
                        }[next_c]
                        result.append(json_char)
                        i += 2
                elif next_c == "u":
                    if i + 5 < n:
                        hex_code = text[i + 2 : i + 6]
                        try:
                            result.append(chr(int(hex_code, 16)))
                            i += 6
                        except ValueError:
                            result.append("\\")
                            result.append(next_c)
                            i += 2
                    else:
                        if not self.completed and len(text) - (i + 2) < 4 and all(ch in "0123456789abcdefABCDEF" for ch in text[i+2:]):
                            break
                        result.append("\\")
                        result.append(next_c)
                        i += 2
                else:
                    # In LaTeX JSON strings, commands like \int, \alpha, \sqrt, \sum, \pm
                    # have single backslashes. Do NOT discard the backslash!
                    result.append("\\")
                    result.append(next_c)
                    i += 2
            elif c == '"':
                self.completed = True
                break
            else:
                result.append(c)
                i += 1
        self.accumulated = "".join(result)


async def _generate_content_stream(
    *,
    model_name: str,
    system_instruction: str,
    parts: list[str | dict[str, bytes | str]],
    agent_name: str = "Tutor Agent",
) -> AsyncGenerator[str, None]:
    client = _get_client(agent_name, model_name)
    contents, config = _build_request(
        model_name=model_name, system_instruction=system_instruction, parts=parts
    )

    max_attempts = max(1, settings.gemini_max_attempts)
    for attempt in range(max_attempts):
        yielded_any = False
        try:
            stream = await client.aio.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config,
            )
            async for chunk in stream:
                text = chunk.text
                if text:
                    yielded_any = True
                    yield text
            return
        except Exception as exc:
            # Retrying after partial output would duplicate text for the client, so only retry
            # when the overload happened before the first chunk.
            if _is_transient_503(exc) and not yielded_any and attempt < max_attempts - 1:
                await asyncio.sleep(_backoff_seconds(attempt))
                continue
            raise _to_service_error(exc, agent_name, model_name) from exc


# ---------------------------------------------------------------------------
# Conversation history helpers
# ---------------------------------------------------------------------------

def _build_history_text(history: list[ConversationMessage], max_messages: int = 10) -> str:
    """
    Convert conversation history to a plain-text block for injection into prompts.
    Sends only the last `max_messages` messages to keep token usage low.
    Screenshots are NOT re-sent — only text content and metadata.
    """
    recent = history[-max_messages:]
    lines: list[str] = []

    for msg in recent:
        prefix = "Student" if msg.role == "user" else "Tutor"
        meta_parts = []

        if msg.message_type:
            meta_parts.append(f"type={msg.message_type.value}")
        if msg.clarification_target:
            meta_parts.append(f"clarifies={msg.clarification_target}")
        if msg.had_screenshot:
            meta_parts.append("had_screenshot=true")

        meta = f" [{', '.join(meta_parts)}]" if meta_parts else ""
        lines.append(f"{prefix}{meta}: {msg.content}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent 0 — Router
# ---------------------------------------------------------------------------

async def router_agent(
    *,
    user_message: str,
    history: list[ConversationMessage],
) -> RouterResult:
    """
    Decides whether the student's message requires a board screenshot,
    and classifies the message type.
    """
    system = ROUTER_AGENT_PROMPT

    history_text = _build_history_text(history, max_messages=6)

    parts = [
        f"Conversation history:\n{history_text}\n" if history_text else "No previous conversation.\n",
        f"Student message: {user_message}",
    ]

    raw = await _generate_content(
        model_name=settings.gemini_model_router,
        system_instruction=system,
        parts=parts,
        agent_name="Router Agent",
    )
    parsed = _parse_json_from_model(raw)

    # Graceful fallback — if parsing fails, assume board is needed
    if parsed.get("_parseError"):
        return RouterResult(
            needs_board=True,
            message_type=MessageType.QUESTION,
            clarification_target=None,
            reasoning="parse_error — defaulting to needs_board=True",
        )

    raw_type = parsed.get("message_type", "question")
    try:
        message_type = MessageType(raw_type)
    except ValueError:
        message_type = MessageType.QUESTION

    return RouterResult(
        needs_board=bool(parsed.get("needs_board", True)),
        message_type=message_type,
        clarification_target=parsed.get("clarification_target"),
        reasoning=str(parsed.get("reasoning", "")),
    )


# ---------------------------------------------------------------------------
# Agent 1+2 — Vision + Parser (Full Board & Patch Agents)
# ---------------------------------------------------------------------------

def _normalize_str(val: Any) -> str:
    if not isinstance(val, str):
        return ""
    return "".join(val.split()).lower()


def _element_signature(el: dict[str, Any]) -> str | None:
    if not isinstance(el, dict):
        return None
    el_type = el.get("type")
    data = el.get("data")
    if not isinstance(data, dict):
        return None

    if el_type == "equation":
        expr = data.get("expression")
        if isinstance(expr, str) and expr.strip():
            return f"eq:{_normalize_str(expr)}"

    elif el_type in ("text", "notes"):
        content = data.get("content")
        if isinstance(content, str) and content.strip():
            return f"text:{' '.join(content.split()).lower()}"

    elif el_type == "problem_statement":
        num = data.get("problem_number")
        content = data.get("content")
        if num:
            return f"prob_num:{_normalize_str(str(num))}"
        if isinstance(content, str) and content.strip():
            return f"prob_content:{' '.join(content.split()).lower()}"

    elif el_type == "shape":
        shape_type = data.get("shape_type", "unknown")
        labels = sorted([_normalize_str(str(l)) for l in data.get("labels", []) if l])
        pos = el.get("position", "")
        if labels:
            return f"shape:{shape_type}:{','.join(labels)}"
        if pos:
            return f"shape:{shape_type}:{pos}"

    return None


def deduplicate_board_context(context: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Cleans up duplicate elements, problems, and warnings from a board context JSON.
    Preserves unique elements while updating existing ones if duplicates exist.
    """
    if not context or not isinstance(context, dict) or context.get("error"):
        return context

    raw_elements = context.get("elements", [])
    deduped_elements: list[dict[str, Any]] = []
    seen_sigs: dict[str, int] = {}

    for el in raw_elements:
        if not isinstance(el, dict):
            continue
        sig = _element_signature(el)
        if sig:
            if sig in seen_sigs:
                existing_idx = seen_sigs[sig]
                existing_id = deduped_elements[existing_idx].get("id")
                updated = dict(el)
                if existing_id:
                    updated["id"] = existing_id
                deduped_elements[existing_idx] = updated
            else:
                seen_sigs[sig] = len(deduped_elements)
                deduped_elements.append(el)
        else:
            deduped_elements.append(el)

    raw_problems = context.get("problem_statements_summary", [])
    deduped_problems: list[dict[str, Any]] = []
    seen_probs: set[str] = set()

    for p in raw_problems:
        if not isinstance(p, dict):
            continue
        p_num = _normalize_str(str(p.get("problem_number", "")))
        p_line = _normalize_str(str(p.get("one_line", "")))
        key = f"num:{p_num}" if p_num else (f"line:{p_line}" if p_line else str(p))
        if key not in seen_probs:
            seen_probs.add(key)
            deduped_problems.append(p)

    def _dedup_list(items: list[Any]) -> list[Any]:
        seen = set()
        out = []
        for it in items:
            key = json.dumps(it, sort_keys=True) if isinstance(it, (dict, list)) else str(it)
            if key not in seen:
                seen.add(key)
                out.append(it)
        return out

    return {
        **context,
        "elements": deduped_elements,
        "problem_statements_summary": deduped_problems,
        "relationships": _dedup_list(context.get("relationships", [])),
        "board_warnings": _dedup_list(context.get("board_warnings", [])),
    }


def merge_board_context(
    existing_context: dict[str, Any] | None,
    patch_result: dict[str, Any],
    patch_bbox: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Merges patch analysis into existing board context JSON.
    Preserves existing elements on other parts of the board, updates elements
    that match by content signature (preventing duplicates), and assigns
    non-colliding IDs to truly new elements.
    """
    if not existing_context or not isinstance(existing_context, dict) or existing_context.get("error"):
        base_elements = []
        content_type = patch_result.get("content_type", "mixed")
        relationships = list(patch_result.get("relationships", []))
        warnings = list(patch_result.get("board_warnings", []))
        problems = list(patch_result.get("problem_statements_summary", []))
    else:
        base_elements = list(existing_context.get("elements", []))
        content_type = existing_context.get("content_type", "mixed")
        relationships = list(existing_context.get("relationships", []))
        warnings = list(existing_context.get("board_warnings", []))
        problems = list(existing_context.get("problem_statements_summary", []))

    replaces = set(patch_result.get("replaces_or_updates_existing_ids", []))
    if replaces:
        base_elements = [el for el in base_elements if isinstance(el, dict) and el.get("id") not in replaces]
        problems = [p for p in problems if isinstance(p, dict) and p.get("element_id") not in replaces]

    # Map existing element signatures to their index in base_elements
    sig_to_index: dict[str, int] = {}
    for idx, el in enumerate(base_elements):
        if isinstance(el, dict):
            sig = _element_signature(el)
            if sig:
                sig_to_index[sig] = idx

    existing_ids = {el.get("id") for el in base_elements if isinstance(el, dict) and el.get("id")}
    counter = 1
    while f"el_{counter}" in existing_ids:
        counter += 1

    new_patch_elements = patch_result.get("elements", [])
    if isinstance(new_patch_elements, list):
        for el in new_patch_elements:
            if not isinstance(el, dict):
                continue

            sig = _element_signature(el)
            # If an element with the exact same content already exists, update in-place without adding duplicate
            if sig and sig in sig_to_index:
                target_idx = sig_to_index[sig]
                target_id = base_elements[target_idx].get("id")
                updated_el = dict(el)
                if target_id:
                    updated_el["id"] = target_id
                if patch_bbox:
                    updated_el["patch_bbox"] = patch_bbox
                base_elements[target_idx] = updated_el
                continue

            orig_id = el.get("id")
            if not orig_id or orig_id in existing_ids or orig_id.startswith("patch_"):
                new_id = f"el_{counter}"
                counter += 1
                while new_id in existing_ids:
                    new_id = f"el_{counter}"
                    counter += 1
                el["id"] = new_id
                existing_ids.add(new_id)
            else:
                existing_ids.add(orig_id)

            if patch_bbox:
                el["patch_bbox"] = patch_bbox
            base_elements.append(el)
            if sig:
                sig_to_index[sig] = len(base_elements) - 1

    # Merge and deduplicate problems
    patch_problems = patch_result.get("problem_statements_summary", [])
    if isinstance(patch_problems, list):
        for p in patch_problems:
            if isinstance(p, dict):
                p_num = _normalize_str(str(p.get("problem_number", "")))
                p_line = _normalize_str(str(p.get("one_line", "")))
                match_idx = None
                for idx, existing_p in enumerate(problems):
                    if not isinstance(existing_p, dict):
                        continue
                    ex_num = _normalize_str(str(existing_p.get("problem_number", "")))
                    ex_line = _normalize_str(str(existing_p.get("one_line", "")))
                    if (p_num and ex_num and p_num == ex_num) or (p_line and ex_line and p_line == ex_line):
                        match_idx = idx
                        break
                if match_idx is not None:
                    problems[match_idx] = p
                else:
                    problems.append(p)

    merged = {
        "content_type": content_type,
        "elements": base_elements,
        "problem_statements_summary": problems,
        "relationships": relationships,
        "board_warnings": warnings,
    }
    return deduplicate_board_context(merged) or merged


async def vision_parser_agent(
    *,
    image_mime: str,
    image_b64: str,
    existing_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Full-board agent: screenshot → structured board JSON.
    Uses the merged vision+parser system prompt.
    """
    system = VISION_AGENT_PROMPT

    parts: list[str | dict[str, bytes | str]] = [
        "Analyze this whiteboard screenshot and return the JSON board context.",
        {
            "mime_type": image_mime,
            "data": base64.b64decode(image_b64),
        },
    ]

    raw = await _generate_content(
        model_name=settings.gemini_model_vision,
        system_instruction=system,
        parts=parts,
        agent_name="Vision Parser Agent",
    )
    if not raw:
        return existing_context or {"error": "empty_vision_response"}

    result = _parse_json_from_model(raw)
    if result.get("_parseError") and existing_context:
        return existing_context
    return deduplicate_board_context(result) or result


async def vision_patch_agent(
    *,
    image_mime: str,
    image_b64: str,
    patch_bbox: dict[str, Any] | None = None,
    existing_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Patch agent: analyzes a focused, high-resolution crop of a modified/new board region
    and merges it cleanly into the existing board context JSON.
    """
    system = VISION_PATCH_PROMPT

    prompt_parts = ["Analyze this high-resolution cropped patch of whiteboard content and return structured JSON."]
    if patch_bbox:
        prompt_parts.append(
            f"Region bounds on canvas: minX={patch_bbox.get('minX')}, minY={patch_bbox.get('minY')}, "
            f"maxX={patch_bbox.get('maxX')}, maxY={patch_bbox.get('maxY')}, "
            f"width={patch_bbox.get('width')}, height={patch_bbox.get('height')}."
        )
    if existing_context and isinstance(existing_context, dict) and existing_context.get("elements"):
        summary_items = [
            f"- {el.get('id')}: {el.get('type')} ({el.get('position', 'unknown')})"
            for el in existing_context.get("elements", [])[:15]
            if isinstance(el, dict)
        ]
        if summary_items:
            prompt_parts.append("Existing whiteboard elements for reference:\n" + "\n".join(summary_items))

    parts: list[str | dict[str, bytes | str]] = [
        "\n\n".join(prompt_parts),
        {
            "mime_type": image_mime,
            "data": base64.b64decode(image_b64),
        },
    ]

    raw = await _generate_content(
        model_name=settings.gemini_model_vision,
        system_instruction=system,
        parts=parts,
        agent_name="Vision Patch Agent",
    )
    if not raw:
        return existing_context or {"error": "empty_vision_response"}

    patch_result = _parse_json_from_model(raw)
    if patch_result.get("_parseError"):
        return existing_context or patch_result

    return merge_board_context(existing_context, patch_result, patch_bbox)


# ---------------------------------------------------------------------------
# Viewport helpers
# ---------------------------------------------------------------------------

def _get_visible_element_ids(
    board_context: dict[str, Any],
    visible_viewport: dict[str, Any],
) -> list[str]:
    """
    Returns IDs of elements whose patch_bbox intersects the visible viewport.
    Falls back to elements matching positional keywords if patch_bbox is absent.
    Pure Python — no AI call needed.
    """
    vp_minx = float(visible_viewport.get("minX", -1e9))
    vp_miny = float(visible_viewport.get("minY", -1e9))
    vp_maxx = float(visible_viewport.get("maxX", 1e9))
    vp_maxy = float(visible_viewport.get("maxY", 1e9))

    POSITION_IN_VIEWPORT = {"top-left", "top-center", "top-right",
                            "center-left", "center", "center-right",
                            "bottom-left", "bottom-center", "bottom-right"}

    visible: list[str] = []
    elements = board_context.get("elements", [])
    if not isinstance(elements, list):
        return visible

    for el in elements:
        if not isinstance(el, dict):
            continue
        el_id = el.get("id")
        if not el_id:
            continue

        bbox = el.get("patch_bbox")
        if isinstance(bbox, dict):
            b_minx = float(bbox.get("minX", 0))
            b_miny = float(bbox.get("minY", 0))
            b_maxx = float(bbox.get("maxX", 0))
            b_maxy = float(bbox.get("maxY", 0))
            intersects = (b_minx <= vp_maxx and b_maxx >= vp_minx
                          and b_miny <= vp_maxy and b_maxy >= vp_miny)
            if intersects:
                visible.append(el_id)
        else:
            # No coordinate info — fall back to positional keyword
            position = el.get("position", "")
            if position in POSITION_IN_VIEWPORT:
                visible.append(el_id)

    return visible


def _build_viewport_hint(
    visible_viewport: dict[str, Any] | None,
    visible_element_ids: list[str],
) -> str:
    """
    Produces a human-readable string describing what the student is looking at.
    Used in the context filter and tutor prompts.
    """
    if not visible_viewport:
        return "No viewport information available — the full board is in scope."

    zoom = visible_viewport.get("zoom", 1.0)
    minx = visible_viewport.get("minX")
    miny = visible_viewport.get("minY")
    maxx = visible_viewport.get("maxX")
    maxy = visible_viewport.get("maxY")

    zoom_label = (
        "zoomed in closely" if zoom > 1.5
        else "zoomed out (broad view)" if zoom < 0.6
        else "at normal zoom"
    )

    coord_str = (f"Scene region: x=[{minx:.0f}, {maxx:.0f}], y=[{miny:.0f}, {maxy:.0f}]."
                 if all(v is not None for v in (minx, miny, maxx, maxy)) else "")

    ids_str = (f"Visible elements: {', '.join(visible_element_ids)}."
               if visible_element_ids else "No specific elements identified in viewport.")

    return f"Student is {zoom_label}. {coord_str} {ids_str}".strip()


# ---------------------------------------------------------------------------
# Agent 2.5 — Context Filter
# ---------------------------------------------------------------------------

async def context_filter_agent(
    *,
    board_context: dict[str, Any],
    user_message: str,
    visible_viewport: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    """
    Context pruning agent: selects only board elements relevant to the student's question.
    Also returns a viewport_hint string for downstream agents.

    Returns (pruned_board_context, viewport_hint).
    Gracefully falls back to the full board_context on any error.
    """
    # Pre-compute visible element IDs (zero-cost, no AI)
    visible_element_ids: list[str] = []
    if visible_viewport and isinstance(board_context, dict):
        visible_element_ids = _get_visible_element_ids(board_context, visible_viewport)

    viewport_hint = _build_viewport_hint(visible_viewport, visible_element_ids)

    # Skip filtering if the board is tiny — no point spending a token budget on it
    elements = board_context.get("elements", [])
    if not isinstance(elements, list) or len(elements) <= 2:
        return board_context, viewport_hint

    parts: list[str] = [
        f"student_question: {user_message}",
        f"visible_element_ids: {json.dumps(visible_element_ids)}",
        f"viewport_hint: {viewport_hint}",
        "board_context:\n" + json.dumps(board_context, ensure_ascii=False, indent=2),
    ]

    raw = await _generate_content(
        model_name=settings.gemini_model_filter,
        system_instruction=CONTEXT_FILTER_AGENT_PROMPT,
        parts=parts,
        agent_name="Context Filter Agent",
    )

    if not raw:
        return board_context, viewport_hint

    parsed = _parse_json_from_model(raw)
    if parsed.get("_parseError") or parsed.get("returns_all") is True:
        return board_context, viewport_hint

    pruned = parsed.get("pruned_board_context")
    if not isinstance(pruned, dict) or not pruned.get("elements"):
        return board_context, viewport_hint

    # Safety: ensure required top-level fields are always present
    for key in ("content_type", "relationships", "board_warnings", "problem_statements_summary"):
        if key not in pruned:
            pruned[key] = board_context.get(key, [] if key != "content_type" else "mixed")

    return pruned, viewport_hint


# ---------------------------------------------------------------------------
# Agent 3 — Tutor
# ---------------------------------------------------------------------------

def _build_tutor_parts(
    *,
    user_message: str,
    message_type: MessageType,
    clarification_target: str | None,
    board_context: dict[str, Any] | None,
    history: list[ConversationMessage],
    visible_viewport: dict[str, Any] | None = None,
    viewport_hint: str | None = None,
) -> list[str]:
    history_text = _build_history_text(history, max_messages=10)

    parts: list[str] = []

    # 1. Conversation history
    if history_text:
        parts.append(f"Conversation history:\n{history_text}")

    # 2. Viewport awareness — prefer the pre-built hint; fall back to raw coords
    if viewport_hint:
        parts.append(
            "Student's CURRENT view on the board:\n"
            + viewport_hint
            + "\n\nFull scene coordinates (for reference):\n"
            + json.dumps(visible_viewport, ensure_ascii=False, indent=2)
            if visible_viewport else
            "Student's CURRENT view on the board:\n" + viewport_hint
        )
    elif visible_viewport:
        parts.append(
            "Student's CURRENT visible viewport on the infinite canvas "
            "(scene coordinates). This is what they are looking at right now — "
            "you still have the board_json below and may use any of it:\n"
            + json.dumps(visible_viewport, ensure_ascii=False, indent=2)
        )
    elif board_context:
        parts.append(
            "Student viewport metadata was not provided. "
            "Use the full board_json without assuming a focus region."
        )

    # 3. Board context (already pruned by context_filter_agent if applicable)
    if board_context:
        ctx_for_tutor = dict(board_context)
        elements = ctx_for_tutor.get("elements", [])
        if isinstance(elements, list) and visible_viewport:
            visible_set = set(_get_visible_element_ids(ctx_for_tutor, visible_viewport))
            ctx_for_tutor["elements"] = [
                {**el, "is_visible_on_screen": el.get("id") in visible_set}
                if isinstance(el, dict)
                else el
                for el in elements
            ]
        label = "Current board context (JSON — pre-filtered to relevant elements):"
        parts.append(label + "\n" + json.dumps(ctx_for_tutor, ensure_ascii=False, indent=2))
    else:
        parts.append("Board context: not available for this message.")

    # 4. Message metadata — helps tutor handle clarifications correctly
    meta_lines = [f"Message type: {message_type.value}"]
    if clarification_target:
        meta_lines.append(f"This message clarifies: {clarification_target}")
    parts.append("\n".join(meta_lines))

    # 5. Student message
    parts.append(f"Student: {user_message}")

    return parts


async def tutor_agent(
    *,
    user_message: str,
    message_type: MessageType,
    clarification_target: str | None,
    board_context: dict[str, Any] | None,
    history: list[ConversationMessage],
    visible_viewport: dict[str, Any] | None = None,
    viewport_hint: str | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """
    Tutor agent: answers the student using board context + conversation history.
    Returns (message, todraw). todraw is None when nothing should be drawn.
    """
    parts = _build_tutor_parts(
        user_message=user_message,
        message_type=message_type,
        clarification_target=clarification_target,
        board_context=board_context,
        history=history,
        visible_viewport=visible_viewport,
        viewport_hint=viewport_hint,
    )

    reply = await _generate_content(
        model_name=settings.gemini_model_tutor,
        system_instruction=TUTOR_AGENT_PROMPT,
        parts=parts,
        agent_name="Tutor Agent",
    )
    return _parse_tutor_response(reply or "")


async def tutor_agent_stream(
    *,
    user_message: str,
    message_type: MessageType,
    clarification_target: str | None,
    board_context: dict[str, Any] | None,
    history: list[ConversationMessage],
    visible_viewport: dict[str, Any] | None = None,
    viewport_hint: str | None = None,
) -> AsyncGenerator[tuple[str, Any], None]:
    """
    Streams tutor answer. Yields:
      ("delta", chunk_text)
      ("done", (reply, todraw))
    """
    parts = _build_tutor_parts(
        user_message=user_message,
        message_type=message_type,
        clarification_target=clarification_target,
        board_context=board_context,
        history=history,
        visible_viewport=visible_viewport,
        viewport_hint=viewport_hint,
    )
    extractor = StreamingJsonStringExtractor("message")
    raw_pieces: list[str] = []

    async for chunk in _generate_content_stream(
        model_name=settings.gemini_model_tutor,
        system_instruction=TUTOR_AGENT_PROMPT,
        parts=parts,
        agent_name="Tutor Agent",
    ):
        raw_pieces.append(chunk)
        delta = extractor.feed(chunk)
        if delta:
            yield ("delta", delta)

    full_raw = "".join(raw_pieces)
    reply, todraw = _parse_tutor_response(full_raw or "")

    # If extractor didn't emit text deltas (e.g. model output unexpected format),
    # emit the parsed reply text as delta so user receives the answer:
    if not extractor.accumulated and reply:
        yield ("delta", reply)

    yield ("done", (reply, todraw))


# ---------------------------------------------------------------------------
# Agent 4 — Draw (todraw → Excalidraw elements)
# ---------------------------------------------------------------------------

async def draw_agent(
    *,
    todraw: dict[str, Any],
    visible_viewport: dict[str, Any] | None = None,
    board_context: dict[str, Any] | None = None,
    existing_element_bboxes: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """
    Convert a structured todraw plan into Excalidraw element objects.
    """
    system = DRAW_AGENT_PROMPT

    parts: list[str] = [
        "todraw plan:\n" + json.dumps(todraw, ensure_ascii=False, indent=2),
    ]
    if visible_viewport:
        parts.append(
            "visible_viewport (scene coordinates):\n"
            + json.dumps(visible_viewport, ensure_ascii=False, indent=2)
        )
    else:
        parts.append(
            "visible_viewport: not provided. Place content around scene origin "
            "with reasonable spacing."
        )
    if board_context:
        parts.append(
            "board_context (for relative placement):\n"
            + json.dumps(board_context, ensure_ascii=False, indent=2)
        )
    if existing_element_bboxes:
        parts.append(
            "existing_element_bboxes (avoid overlaps):\n"
            + json.dumps(existing_element_bboxes, ensure_ascii=False, indent=2)
        )

    raw = await _generate_content(
        model_name=settings.gemini_model_draw,
        system_instruction=system,
        parts=parts,
        agent_name="Draw Agent",
    )
    parsed = _parse_json_from_model(raw or "")
    if parsed.get("_parseError"):
        raise ValueError("Draw agent returned invalid JSON")

    elements = parsed.get("elements")
    if not isinstance(elements, list):
        elements = []
    cleaned: list[dict[str, Any]] = [el for el in elements if isinstance(el, dict)]
    notes = parsed.get("notes")
    notes_str = notes.strip() if isinstance(notes, str) and notes.strip() else None
    return cleaned, notes_str


async def prepare_tutor_context(
    *,
    board_context: dict[str, Any] | None,
    user_message: str,
    visible_viewport: dict[str, Any] | None,
    needs_board: bool,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Prunes the board context for the tutor and builds the viewport hint.

    Returns (context_for_tutor, viewport_hint). The full context must still be persisted by the
    caller; the pruned copy is only used for the tutor prompt. Never raises: any filter failure
    falls back to the full context so the filter can only save tokens, never break an answer.
    """
    if (
        not board_context
        or not isinstance(board_context, dict)
        or board_context.get("error")
    ):
        return board_context, None

    if not needs_board:
        # Conversational turn (thanks / short answer) — no reason to spend a filter call.
        return board_context, None

    try:
        return await context_filter_agent(
            board_context=board_context,
            user_message=user_message,
            visible_viewport=visible_viewport,
        )
    except Exception:
        hint = _build_viewport_hint(visible_viewport, []) if visible_viewport else None
        return board_context, hint


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run_pipeline(
    *,
    user_message: str,
    history: list[ConversationMessage],
    image_mime: str | None = None,
    image_b64: str | None = None,
    visible_viewport: dict[str, Any] | None = None,
    patch_bbox: dict[str, Any] | None = None,
    existing_board_context: dict[str, Any] | None = None,
) -> PipelineResult:
    """
    Full pipeline:
      1. Router  — should we use the board?
      2. Vision+Parser (Agent 1+2) — patch/full vision or reuse existing board context
      3. Tutor (Agent 3) — answer with history + optional board context + todraw

    Returns PipelineResult with reply, board_context, todraw, router decision,
    and an enriched ConversationMessage ready to append to history.
    """

    # Step 1 — Route
    router = await router_agent(user_message=user_message, history=history)

    # Step 2 — Vision+Parser (only if needed and image available / cached)
    board_context: dict[str, Any] | None = None
    had_screenshot = False

    if router.needs_board:
        if image_mime and image_b64:
            if patch_bbox and existing_board_context:
                board_context = await vision_patch_agent(
                    image_mime=image_mime,
                    image_b64=image_b64,
                    patch_bbox=patch_bbox,
                    existing_context=existing_board_context,
                )
            else:
                board_context = await vision_parser_agent(
                    image_mime=image_mime,
                    image_b64=image_b64,
                    existing_context=existing_board_context,
                )
            had_screenshot = True
        elif existing_board_context:
            # Reusing existing synced board context
            board_context = existing_board_context
            had_screenshot = True
        else:
            # Router wanted board but no image or cached context was available
            board_context = {"error": "screenshot_not_provided"}
    elif existing_board_context:
        # Board context available in background even if router didn't strictly need fresh view
        board_context = existing_board_context

    # Step 2.5 — Context filter (tutor sees only relevant elements; full context is still persisted)
    tutor_context, viewport_hint = await prepare_tutor_context(
        board_context=board_context,
        user_message=user_message,
        visible_viewport=visible_viewport if had_screenshot else None,
        needs_board=router.needs_board,
    )

    # Step 3 — Tutor
    reply, todraw = await tutor_agent(
        user_message=user_message,
        message_type=router.message_type,
        clarification_target=router.clarification_target,
        board_context=tutor_context,
        history=history,
        visible_viewport=visible_viewport if had_screenshot else None,
        viewport_hint=viewport_hint,
    )

    # Build enriched user message for history
    user_msg = ConversationMessage(
        role="user",
        content=user_message,
        message_type=router.message_type,
        clarification_target=router.clarification_target,
        had_screenshot=had_screenshot,
        board_context=board_context,
    )

    return PipelineResult(
        reply=reply,
        board_context=board_context,
        todraw=todraw,
        router=router,
        message=user_msg,
    )


async def run_pipeline_stream(
    *,
    user_message: str,
    history: list[ConversationMessage],
    image_mime: str | None = None,
    image_b64: str | None = None,
    visible_viewport: dict[str, Any] | None = None,
    patch_bbox: dict[str, Any] | None = None,
    existing_board_context: dict[str, Any] | None = None,
) -> AsyncGenerator[tuple[str, Any], None]:
    """
    Streams full pipeline execution:
      1. yield ("status", {"stage": "routing", "message": "Analyzing question..."})
      2. yield ("status", {"stage": "vision", "message": "Inspecting whiteboard elements..."}) [if needed]
      3. yield ("status", {"stage": "tutor", "message": "Tutor is writing response..."})
      4. yield ("delta", chunk_text)
      5. yield ("done", PipelineResult(...))
    """
    yield ("status", {"stage": "routing", "message": "Analyzing question..."})
    router = await router_agent(user_message=user_message, history=history)

    board_context: dict[str, Any] | None = None
    had_screenshot = False

    if router.needs_board:
        yield ("status", {"stage": "vision", "message": "Inspecting whiteboard..."})
        if image_mime and image_b64:
            if patch_bbox and existing_board_context:
                board_context = await vision_patch_agent(
                    image_mime=image_mime,
                    image_b64=image_b64,
                    patch_bbox=patch_bbox,
                    existing_context=existing_board_context,
                )
            else:
                board_context = await vision_parser_agent(
                    image_mime=image_mime,
                    image_b64=image_b64,
                    existing_context=existing_board_context,
                )
            had_screenshot = True
        elif existing_board_context:
            board_context = existing_board_context
            had_screenshot = True
        else:
            board_context = {"error": "screenshot_not_provided"}
    elif existing_board_context:
        board_context = existing_board_context

    tutor_context, viewport_hint = await prepare_tutor_context(
        board_context=board_context,
        user_message=user_message,
        visible_viewport=visible_viewport if had_screenshot else None,
        needs_board=router.needs_board,
    )

    yield ("status", {"stage": "tutor", "message": "Tutor is writing response..."})

    reply: str = ""
    todraw: dict[str, Any] | None = None

    async for kind, payload in tutor_agent_stream(
        user_message=user_message,
        message_type=router.message_type,
        clarification_target=router.clarification_target,
        board_context=tutor_context,
        history=history,
        visible_viewport=visible_viewport if had_screenshot else None,
        viewport_hint=viewport_hint,
    ):
        if kind == "delta":
            yield ("delta", payload)
        elif kind == "done":
            reply, todraw = payload

    user_msg = ConversationMessage(
        role="user",
        content=user_message,
        message_type=router.message_type,
        clarification_target=router.clarification_target,
        had_screenshot=had_screenshot,
        board_context=board_context,
    )

    result = PipelineResult(
        reply=reply,
        board_context=board_context,
        todraw=todraw,
        router=router,
        message=user_msg,
    )
    yield ("done", result)