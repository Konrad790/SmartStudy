/** Strip optional data-URL prefix and whitespace from a base64 payload. */
export function normalizeBase64ImagePayload(base64: string): string {
  const trimmed = base64.trim();
  const match = /^data:[^;]+;base64,(.+)$/i.exec(trimmed);
  return (match ? match[1] : trimmed).replace(/\s/g, "");
}
