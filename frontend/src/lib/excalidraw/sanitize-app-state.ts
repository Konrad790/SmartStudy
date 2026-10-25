/** Excalidraw expects `appState.collaborators` to be a Map; JSON persistence turns it into `{}`. */
export function sanitizeAppState(raw: unknown): Record<string, unknown> {
  if (!raw || typeof raw !== "object") {
    return { collaborators: new Map() };
  }
  const next = { ...(raw as Record<string, unknown>) };
  if (!(next.collaborators instanceof Map)) {
    next.collaborators = new Map();
  }
  return next;
}
