/**
 * Cleans up and prepares AI tutor message text for ReactMarkdown + KaTeX rendering.
 * Fixes escaped newlines, LaTeX commands, bare delimiters, and leaked JSON wrappers.
 */

const PROTECTED_BLOCKS = /(```[\s\S]*?```|`[^`\n]*`|\$\$[\s\S]*?\$\$|\$[^$\n]+\$)/g;

export function formatAssistantText(raw: string): string {
  if (!raw) return "";

  let text = raw;

  // 1. Strip leaked JSON wrapper if present (e.g. `{"message": "..."}` or markdown code fences)
  const jsonWrapperMatch = text.match(/^\s*(?:```(?:json)?\s*)?\{\s*"message"\s*:\s*"([\s\S]*?)"(?:\s*,\s*"todraw"[\s\S]*)?\}\s*(?:```)?\s*$/i);
  if (jsonWrapperMatch) {
    text = jsonWrapperMatch[1];
  } else {
    // If just fenced in ```json ... ```, strip the fence
    text = text.replace(/^\s*```(?:json|markdown)?\s*\n?([\s\S]*?)\n?```\s*$/i, "$1");
  }

  // 2. Normalize standard LaTeX display/inline delimiters to $ / $$ for remark-math
  text = text.replace(/\\\[([\s\S]+?)\\\]/g, (_, math) => `\n$$${math.trim()}$$\n`);
  text = text.replace(/\\\((.+?)\\\)/g, (_, math) => `$${math.trim()}$`);

  // 3. Process unprotected segments (outside existing $...$, $$...$$, code blocks)
  const segments = text.split(PROTECTED_BLOCKS);
  for (let i = 0; i < segments.length; i += 2) {
    let seg = segments[i];

    // Replace literal escaped newlines "\n" that are NOT LaTeX commands (\neq, \nabla, \notin, \newline, \nu)
    seg = seg.replace(/\\n(?!eq(?![a-zA-Z])|abla(?![a-zA-Z])|otin(?![a-zA-Z])|ewline|u(?![a-zA-Z]))/g, "\n");

    // Replace literal escaped quotes
    seg = seg.replace(/\\"/g, '"');

    // Auto-wrap bare LaTeX commands (e.g. \int_0^1 x^2 dx, \frac{a}{b}, \sqrt{x}) in $...$
    // so remark-math and KaTeX render them as symbols rather than raw text.
    seg = seg.replace(/\\(?:d?frac|binom)\s*\{[^{}]*\}\s*\{[^{}]*\}/g, (m) => `$${m}$`);
    seg = seg.replace(/\\sqrt(?:\s*\[[^[\]]*\])?\s*\{[^{}]*\}/g, (m) => `$${m}$`);
    seg = seg.replace(/\\(?:int|oint)(?:\s*[_^]\s*(?:\{[^{}]*\}|[a-zA-Z0-9]+))*(?:\s*[^$\n]{0,60}?\bd[xyzts](?![a-zA-Z]))?/g, (m) => `$${m}$`);

    // Common ASCII arrows and relations
    seg = seg.replace(/<=(?!\w)/g, "≤");
    seg = seg.replace(/>=(?!\w)/g, "≥");
    seg = seg.replace(/!=(?!\w)/g, "≠");
    seg = seg.replace(/->(?!\w)/g, "→");

    segments[i] = seg;
  }

  return segments.join("").trim();
}
