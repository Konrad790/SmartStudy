import asyncio
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/test")
os.environ.setdefault("CLERK_JWKS_URL", "https://example.clerk.accounts.dev/.well-known/jwks.json")

import pytest  # noqa: E402
from google.genai import errors as genai_errors  # noqa: E402

from app import ratelimit  # noqa: E402
from app.config import settings  # noqa: E402
from app.services import gemini  # noqa: E402


def run(coro):
    return asyncio.run(coro)


# --- rate limiter -----------------------------------------------------------


def test_rate_limit_blocks_after_limit_and_recovers():
    ratelimit.reset_rate_limits()
    assert ratelimit._check("u1", 2, now=0.0) is None
    assert ratelimit._check("u1", 2, now=1.0) is None
    wait = ratelimit._check("u1", 2, now=2.0)
    assert wait is not None and 57 < wait <= 60
    # other users are unaffected
    assert ratelimit._check("u2", 2, now=2.0) is None
    # window slides
    assert ratelimit._check("u1", 2, now=61.0) is None


# --- retry for 503 ------------------------------------------------------------


class _FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def generate_content(self, **_kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return type("R", (), {"text": outcome})()


class _FakeClient:
    def __init__(self, models):
        self.aio = type("Aio", (), {"models": models})()


def _patch(monkeypatch, outcomes):
    models = _FakeModels(outcomes)
    monkeypatch.setattr(gemini, "_get_client", lambda *_a, **_k: _FakeClient(models))

    async def no_sleep(_s):
        return None

    monkeypatch.setattr(gemini.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(settings, "gemini_max_attempts", 3)
    return models


def _503():
    return genai_errors.APIError(503, {"error": {"message": "overloaded", "status": "UNAVAILABLE"}})


def test_503_is_retried_then_succeeds(monkeypatch):
    models = _patch(monkeypatch, [_503(), _503(), " ok "])
    out = run(gemini._generate_content(model_name="gemini-x", system_instruction="s", parts=["hi"]))
    assert out == "ok"
    assert models.calls == 3


def test_503_gives_up_after_max_attempts(monkeypatch):
    models = _patch(monkeypatch, [_503(), _503(), _503()])
    with pytest.raises(gemini.AIServiceError) as err:
        run(gemini._generate_content(model_name="gemini-x", system_instruction="s", parts=["hi"]))
    assert "503" in err.value.message
    assert models.calls == 3


def test_429_fails_fast(monkeypatch):
    rate = genai_errors.APIError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    models = _patch(monkeypatch, [rate, "never"])
    with pytest.raises(gemini.AIServiceError) as err:
        run(gemini._generate_content(model_name="gemini-x", system_instruction="s", parts=["hi"]))
    assert "429" in err.value.message
    assert models.calls == 1


def test_build_request_gemma_inlines_system_prompt():
    contents, config = gemini._build_request(
        model_name="gemma-3-27b-it",
        system_instruction="SYS",
        parts=["a", {"mime_type": "image/png", "data": b"\x89PNG"}],
    )
    assert config is None
    assert contents[0] == "SYS" and contents[1] == "a"
    assert contents[2].inline_data.mime_type == "image/png"


def test_build_request_gemini_uses_system_instruction():
    contents, config = gemini._build_request(model_name="gemini-2.5-flash", system_instruction="SYS", parts=["a"])
    assert config.system_instruction == "SYS"
    assert contents == ["a"]


# --- context filter wiring ------------------------------------------------------


def test_prepare_tutor_context_falls_back_on_filter_error(monkeypatch):
    async def boom(**_k):
        raise gemini.AIServiceError("x", service="Context Filter Agent")

    monkeypatch.setattr(gemini, "context_filter_agent", boom)
    ctx = {"elements": [{"id": "el_1"}, {"id": "el_2"}, {"id": "el_3"}]}
    vp = {"minX": 0, "minY": 0, "maxX": 10, "maxY": 10, "zoom": 1.0}
    out, hint = run(
        gemini.prepare_tutor_context(board_context=ctx, user_message="q", visible_viewport=vp, needs_board=True)
    )
    assert out is ctx
    assert hint and "normal zoom" in hint


def test_prepare_tutor_context_skips_filter_when_board_not_needed(monkeypatch):
    called = False

    async def spy(**_k):
        nonlocal called
        called = True
        return {}, ""

    monkeypatch.setattr(gemini, "context_filter_agent", spy)
    ctx = {"elements": [{"id": "el_1"}]}
    out, hint = run(
        gemini.prepare_tutor_context(board_context=ctx, user_message="thanks", visible_viewport=None, needs_board=False)
    )
    assert out is ctx and hint is None and not called


def test_prepare_tutor_context_passes_through_error_context():
    ctx = {"error": "screenshot_not_provided"}
    out, hint = run(
        gemini.prepare_tutor_context(board_context=ctx, user_message="q", visible_viewport=None, needs_board=True)
    )
    assert out is ctx and hint is None


# --- existing logic worth locking in -----------------------------------------------


def test_merge_board_context_renumbers_colliding_ids():
    existing = {"elements": [{"id": "el_1"}], "content_type": "math"}
    patch = {"elements": [{"id": "patch_el_1"}, {"id": "el_1"}], "patch_summary": "b"}
    merged = gemini.merge_board_context(existing, patch, {"minX": 0})
    ids = [e["id"] for e in merged["elements"]]
    assert len(ids) == len(set(ids)) == 3
    assert "overall_context" not in merged


def test_streaming_extractor_decodes_escapes_across_chunks():
    ex = gemini.StreamingJsonStringExtractor("message")
    text = ""
    # the \u0042 escape ("B") is split across two chunks
    for chunk in ['{"mess', 'age": "Hi\\n', "x\\u00", '42 there", "todraw": null}']:
        text += ex.feed(chunk)
    assert text == "Hi\nxB there"


def test_streaming_extractor_preserves_latex_and_handles_escapes():
    ex = gemini.StreamingJsonStringExtractor("message")
    text = ""
    # Model sends \int, \frac, \neq, and normal \n
    raw = r'{"message": "Oblicz: $\int_0^1 x^2 dx$\nWynik: $\frac{1}{3}$\nWarunek: $a \neq 0$", "todraw": null}'
    for chunk in [raw[:25], raw[25:50], raw[50:]]:
        text += ex.feed(chunk)
    assert r"\int" in text
    assert r"\frac" in text
    assert r"\neq" in text
    assert "\n" in text  # literal \n became real newline


def test_parse_json_from_model_survives_raw_latex_escapes():
    # Model generates JSON with invalid escapes like \i in \int and \s in \sqrt
    raw = r'{"message": "Oblicz $\int x dx$ oraz $\sqrt{x}$", "todraw": null}'
    parsed = gemini._parse_json_from_model(raw)
    assert not parsed.get("_parseError")
    assert r"\int" in parsed["message"]
    assert r"\sqrt" in parsed["message"]


def test_format_tutor_message_converts_plain_math_and_cleans_json():
    # If model leaks JSON wrapper or writes plain int instead of LaTeX
    raw = r'{"message": "Krok 1: int_0^1 x dx = 1/2\nKrok 2: \[ x^2 = 4 \]"}'
    cleaned = gemini.format_tutor_message(raw)
    assert "{" not in cleaned
    assert r"\int" in cleaned
    assert "$$" in cleaned  # \[ \] converted to $$ $$


def test_format_conversation_title():
    from app.services.assistant import _format_conversation_title

    assert _format_conversation_title("") == "Nowa konwersacja"
    assert _format_conversation_title("   ") == "Nowa konwersacja"
    assert _format_conversation_title("Jak rozwiazac to rownanie?") == "Jak rozwiazac to rownanie?"
    long_msg = "To jest bardzo długa wiadomość użytkownika która przekracza trzydzieści sześć znaków"
    formatted = _format_conversation_title(long_msg)
    assert formatted.endswith("…")
    assert len(formatted) <= 40


def test_chat_schemas_conversation_id():
    from app.schemas import ChatIn, ChatOut, ConversationOut

    chat_in = ChatIn(message="Cześć", conversationId="conv-123")
    assert chat_in.conversationId == "conv-123"

    chat_out = ChatOut(message="Hej", conversationId="conv-123")
    assert chat_out.conversationId == "conv-123"

    conv_out = ConversationOut(
        id="conv-1",
        boardId="board-1",
        title="Test",
        createdAt="2026-10-25T10:00:00Z",
        updatedAt="2026-10-25T10:00:00Z",
        messageCount=5,
        lastMessagePreview="Ostatnia wiadomosc",
    )
    assert conv_out.messageCount == 5
    assert conv_out.lastMessagePreview == "Ostatnia wiadomosc"


def test_merge_board_context_deduplicates_same_equations():
    existing = {
        "elements": [
            {"id": "el_1", "type": "equation", "data": {"expression": "x^2 + 2x = 0"}}
        ],
        "content_type": "math",
    }
    # Patch contains the same equation with different whitespace and a new confidence
    patch = {
        "elements": [
            {
                "id": "patch_el_1",
                "type": "equation",
                "confidence": "high",
                "data": {"expression": " x^2 + 2x=0 "},
            }
        ],
        "problem_statements_summary": [{"problem_number": "1", "one_line": "solve quadratic"}],
    }
    merged = gemini.merge_board_context(existing, patch, {"minX": 10, "minY": 20})

    # Must NOT create a duplicate element — should update el_1
    assert len(merged["elements"]) == 1
    assert merged["elements"][0]["id"] == "el_1"
    assert merged["elements"][0]["confidence"] == "high"
    assert merged["elements"][0]["patch_bbox"] == {"minX": 10, "minY": 20}


def test_merge_board_context_deduplicates_problem_summaries():
    existing = {
        "elements": [],
        "problem_statements_summary": [
            {"problem_number": "1", "one_line": "Initial summary"}
        ],
    }
    patch = {
        "elements": [],
        "problem_statements_summary": [
            {"problem_number": "1", "one_line": "Updated summary from patch"}
        ],
    }
    merged = gemini.merge_board_context(existing, patch)
    assert len(merged["problem_statements_summary"]) == 1
    assert merged["problem_statements_summary"][0]["one_line"] == "Updated summary from patch"


def test_deduplicate_board_context_cleans_accumulated_duplicates():
    raw_context = {
        "elements": [
            {"id": "el_1", "type": "equation", "data": {"expression": "a + b = c"}},
            {"id": "el_2", "type": "equation", "data": {"expression": "a+b=c"}},
            {"id": "el_3", "type": "text", "data": {"content": "Hello World"}},
            {"id": "el_4", "type": "text", "data": {"content": "hello world"}},
            {"id": "el_5", "type": "equation", "data": {"expression": "y = 2x"}},
        ],
        "problem_statements_summary": [
            {"problem_number": "1", "one_line": "Task 1"},
            {"problem_number": "1", "one_line": "Task 1 duplicate"},
        ],
        "board_warnings": ["bad_contrast", "bad_contrast"],
    }
    cleaned = gemini.deduplicate_board_context(raw_context)
    assert len(cleaned["elements"]) == 3  # (a+b=c), (hello world), (y=2x)
    assert len(cleaned["problem_statements_summary"]) == 1
    assert cleaned["board_warnings"] == ["bad_contrast"]


