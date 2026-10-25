"""Normalisation of tutor replies before they are stored / shown.

The tutor answers with JSON, which is fragile for LaTeX (`\\int`, `\\frac`, `\\neq`, ...):
broken escapes leak JSON fragments, literal "\\n" sequences or swallowed backslashes ("int" instead of
the integral sign). `format_tutor_message` is the safety net that makes the text render well as
Markdown + KaTeX (`$...$`, `$$...$$`) no matter how the model formatted it.

Keep in sync with `frontend/src/lib/utils/format-assistant-text.ts`.
"""

import re

# --- JSON escape handling for LaTeX ---------------------------------------------------------
#
# Models put LaTeX straight into JSON strings. `\int`, `\alpha`, `\sqrt` are invalid JSON escapes
# (parse error or a dropped backslash) and `\frac`, `\neq`, `\times`, `\beta`, `\rho` are *valid*
# escapes that silently decode to control characters. Names below are the LaTeX commands that
# start with one of the JSON escape letters; when the letter is followed by one of them, the
# backslash is LaTeX, not an escape.
_AMBIGUOUS_COMMANDS: dict[str, tuple[str, ...]] = {
    "b": ("eta", "ar", "inom", "oldsymbol", "egin", "ig", "ullet", "ecause", "ot", "mod", "f"),
    "f": ("rac", "orall", "lat", "loor", "box"),
    "n": ("eq", "abla", "otin", "u", "ewline", "ot", "i", "e", "less", "mid", "parallel", "subseteq"),
    "r": ("ho", "ightarrow", "ight", "angle", "floor", "ceil", "m"),
    "t": ("imes", "heta", "ext", "au", "an", "o", "riangle", "ilde", "op", "frac", "extbf"),
}
_HEX = set("0123456789abcdefABCDEF")


def classify_escape(text: str, i: int, *, final: bool) -> str:
    """Decide what the backslash at `text[i]` (followed by a letter) means inside a JSON string.

    Returns:
      "keep"  - a genuine JSON escape (\\n, \\t, \\uXXXX ...)
      "latex" - the backslash belongs to a LaTeX command and must be preserved literally
      "wait"  - cannot decide yet (streaming: the chunk ended mid-command); only when final=False
    """
    letter = text[i + 1]
    rest = text[i + 2 :]

    if letter == "u":
        digits = rest[:4]
        if len(digits) == 4 and all(ch in _HEX for ch in digits):
            return "keep"
        if not final and len(digits) < 4 and all(ch in _HEX for ch in digits):
            return "wait"
        return "latex"  # \upsilon, \underline, \uparrow ...

    candidates = _AMBIGUOUS_COMMANDS.get(letter)
    if candidates is None:
        # \\ \" \/ are handled by callers; any other letter is not a JSON escape at all
        return "latex" if letter not in "bfnrt" else "keep"

    for suffix in candidates:
        if rest.startswith(suffix):
            follow = rest[len(suffix) : len(suffix) + 1]
            if follow == "":
                if not final:
                    return "wait"
                return "latex"
            if not follow.isalpha():
                return "latex"
        elif not final and suffix.startswith(rest) and len(rest) < len(suffix):
            return "wait"
    return "keep"


def escape_latex_in_json(raw: str) -> str:
    """Double the backslashes that are LaTeX (or otherwise invalid escapes) so `json.loads` keeps them."""
    out: list[str] = []
    i, n = 0, len(raw)
    while i < n:
        ch = raw[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= n:
            out.append("\\\\")
            i += 1
            continue
        nxt = raw[i + 1]
        if nxt in '\\"/':
            out.append(ch + nxt)
            i += 2
        elif nxt.isalpha() and classify_escape(raw, i, final=True) == "keep":
            out.append(ch + nxt)
            i += 2
        else:
            out.append("\\\\")
            i += 1
    return "".join(out)


# Segments that must never be rewritten: code blocks, inline code, display and inline math.
_PROTECTED = re.compile(r"(```[\s\S]*?```|`[^`\n]*`|\$\$[\s\S]*?\$\$|\$[^$\n]+\$)")

_JSON_PREFIX = re.compile(r'^\s*(?:```(?:json)?\s*)?\{\s*"message"\s*:\s*"', re.IGNORECASE)
_JSON_SUFFIX = re.compile(r'"\s*(?:,\s*"todraw"[\s\S]*)?\}\s*(?:```)?\s*$')
_FENCE_ONLY = re.compile(r"^\s*```(?:json|markdown|md)?\s*\n([\s\S]*?)\n?```\s*$", re.IGNORECASE)

# JSON decoding turned the first characters of some LaTeX commands into control characters:
# \f(rac) -> form feed, \t(imes) -> tab, \b(eta) -> backspace, \r(ho) -> CR.
_CONTROL_REPAIRS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\x0c(?=rac|lat)"), r"\\f"),
    (re.compile(r"\t(?=imes|heta|ext|au(?![a-z])|an(?![a-z])|o(?![a-z])|riangle|ilde|op(?![a-z]))"), r"\\t"),
    (re.compile(r"\x08(?=eta|ar(?![a-z])|inom|oldsymbol|egin|ig(?![a-z]))"), r"\\b"),
    (re.compile(r"\r(?=ho(?![a-z])|ightarrow|ight(?![a-z])|angle|floor|ceil)"), r"\\r"),
    (re.compile(r"\n(?=eq(?![A-Za-z])|abla(?![A-Za-z])|otin(?![A-Za-z]))"), r"\\n"),
)

# Literal "\n" that is NOT the start of a LaTeX command (\neq, \nabla, \notin, \newline, \nu...).
_LITERAL_NEWLINE = re.compile(r"\\n(?!eq(?![A-Za-z])|abla(?![A-Za-z])|otin(?![A-Za-z])|ewline|u(?![A-Za-z]))")

_UNICODE_SYMBOLS: dict[str, str] = {
    "int": "∫", "oint": "∮", "sum": "∑", "prod": "∏", "infty": "∞", "pi": "π", "alpha": "α",
    "beta": "β", "gamma": "γ", "delta": "δ", "Delta": "Δ", "theta": "θ", "lambda": "λ", "mu": "μ",
    "sigma": "σ", "Sigma": "Σ", "omega": "ω", "Omega": "Ω", "phi": "φ", "epsilon": "ε",
    "partial": "∂", "nabla": "∇", "cdot": "·", "times": "×", "div": "÷", "pm": "±", "mp": "∓",
    "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠", "approx": "≈",
    "equiv": "≡", "to": "→", "rightarrow": "→", "leftarrow": "←", "Rightarrow": "⇒",
    "Leftrightarrow": "⇔", "in": "∈", "notin": "∉", "subset": "⊂", "cup": "∪", "cap": "∩",
    "forall": "∀", "exists": "∃", "degree": "°", "circ": "°", "angle": "∠", "perp": "⊥",
    "parallel": "∥", "sqrt": "√",
}
_SYMBOL_CMD = re.compile(r"\\(" + "|".join(sorted(_UNICODE_SYMBOLS, key=len, reverse=True)) + r")(?![A-Za-z])")

_SCRIPTS = r"(?:\s*[_^]\s*(?:\{[^{}]*\}|\\?[A-Za-z0-9]+))"
# Self-contained LaTeX found outside of math delimiters -> wrap in $...$
_BARE_LATEX = re.compile(
    r"\\(?:d?frac|binom)(?![A-Za-z])(?:\s*\{[^{}]*\}){2}"
    r"|\\sqrt(?![A-Za-z])(?:\s*\[[^\[\]]*\])?\s*\{[^{}]*\}"
    r"|\\(?:int|oint)(?![A-Za-z])" + _SCRIPTS + r"*(?:[^$\n]{0,80}?\bd[xyzts](?![A-Za-z]))?"
)
# Plain-text forms models like to write: "int_0^1 x^2 dx", "int x dx", "sqrt(x+1)"
_PLAIN_INTEGRAL_LIMITS = re.compile(
    r"(?<![\w\\])int(" + _SCRIPTS + r"+)([^$\n]{0,80}?\bd[xyzts](?![A-Za-z]))?"
)
_PLAIN_INTEGRAL = re.compile(r"(?<![\w\\$])int\s+([^$\n]{1,60}?\bd[xyzts](?![A-Za-z]))")
_PLAIN_SQRT = re.compile(r"(?<![\w\\])sqrt\(([^()\n]{1,40})\)")


def _map_segments(text: str, fn) -> str:
    """Apply `fn` to every part of `text` that is not code or math."""
    parts = _PROTECTED.split(text)
    # re.split with a capture group puts the protected segments at odd indices
    return "".join(part if i % 2 else fn(part) for i, part in enumerate(parts))


def _strip_json_wrapper(text: str) -> str:
    fence = _FENCE_ONLY.match(text)
    if fence:
        text = fence.group(1)
    if _JSON_PREFIX.match(text):
        text = _JSON_PREFIX.sub("", text, count=1)
        text = _JSON_SUFFIX.sub("", text, count=1)
        text = text.replace('\\"', '"').replace("\\\\", "\\")
    return text


def _repair_control_chars(text: str) -> str:
    for pattern, replacement in _CONTROL_REPAIRS:
        text = pattern.sub(lambda _m, r=replacement: r.replace("\\\\", "\\"), text)
    return text


def _unescape_literals(text: str) -> str:
    text = _LITERAL_NEWLINE.sub("\n", text)
    return text.replace('\\"', '"')


def _normalize_delimiters(text: str) -> str:
    text = re.sub(r"\\\[([\s\S]+?)\\\]", lambda m: f"\n$${m.group(1).strip()}$$\n", text)
    return re.sub(r"\\\((.+?)\\\)", lambda m: f"${m.group(1).strip()}$", text)


def _wrap_plain_math(segment: str) -> str:
    segment = _PLAIN_INTEGRAL_LIMITS.sub(lambda m: f"$\\int{m.group(1)}{m.group(2) or ''}$", segment)
    segment = _PLAIN_INTEGRAL.sub(lambda m: f"$\\int {m.group(1)}$", segment)
    segment = _PLAIN_SQRT.sub(lambda m: f"$\\sqrt{{{m.group(1)}}}$", segment)
    return _BARE_LATEX.sub(lambda m: f"${m.group(0).strip()}$", segment)


def _symbols_to_unicode(segment: str) -> str:
    segment = _SYMBOL_CMD.sub(lambda m: _UNICODE_SYMBOLS[m.group(1)], segment)
    for ascii_op, symbol in (("<=", "≤"), (">=", "≥"), ("!=", "≠"), ("->", "→")):
        segment = segment.replace(ascii_op, symbol)
    return segment


def format_tutor_message(text: str) -> str:
    """Return `text` cleaned up for Markdown + KaTeX rendering. Idempotent."""
    if not text:
        return text
    cleaned = _strip_json_wrapper(text)
    cleaned = _repair_control_chars(cleaned)
    cleaned = _unescape_literals(cleaned)
    cleaned = _normalize_delimiters(cleaned)
    cleaned = _map_segments(cleaned, _wrap_plain_math)
    cleaned = _map_segments(cleaned, _symbols_to_unicode)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
