export type ApiErrorPayload = {
  message?: string;
  code?: string;
  service?: string;
  detail?: string | { message?: string; service?: string; code?: string };
};

export async function parseJsonOrThrow<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    if (isJson) {
      const payload = (await response.json()) as ApiErrorPayload;
      let msg = payload.message;
      let srv = payload.service;

      if (!msg && typeof payload.detail === "string") {
        msg = payload.detail;
      } else if (typeof payload.detail === "object" && payload.detail) {
        msg = msg ?? payload.detail.message;
        srv = srv ?? payload.detail.service;
      }

      msg = msg ?? `Request failed (${response.status})`;
      const fullMsg = srv && !msg.includes(srv) ? `[${srv}] ${msg}` : msg;
      throw new Error(fullMsg);
    }
    throw new Error(`Request failed (${response.status})`);
  }

  if (!isJson) {
    throw new Error(
      "API returned a non-JSON response. Is FastAPI running? Start it with npm run dev:api."
    );
  }
  return (await response.json()) as T;
}
