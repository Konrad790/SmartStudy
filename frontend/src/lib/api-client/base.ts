const DEFAULT_DIRECT_API = "http://127.0.0.1:8000";
const API_PROXY_PATH = "/backend-api";

/** Direct FastAPI URL for server-side calls. */
export function getDirectApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  return configured?.replace(/\/$/, "") || DEFAULT_DIRECT_API;
}

/**
 * Base URL for browser `fetch`. Talks to FastAPI directly when NEXT_PUBLIC_API_URL
 * is set. Same-origin `/backend-api` proxy is opt-in (NEXT_PUBLIC_API_PROXY=true)
 * because Clerk middleware can swallow those rewrites as HTML 404s.
 */
export function getApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return getDirectApiBaseUrl();
  }
  if (process.env.NEXT_PUBLIC_API_PROXY === "true") {
    return API_PROXY_PATH;
  }
  return getDirectApiBaseUrl();
}
