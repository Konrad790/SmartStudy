"use client";

import { getApiBaseUrl } from "@/lib/api-client/base";
import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";

export function useApiClient() {
  const { getToken, isLoaded, isSignedIn } = useAuth();

  const fetchWithAuth = useCallback(
    async (path: string, init?: RequestInit) => {
      const token = await getToken({ skipCache: false });
      if (!token) {
        throw new Error("Unauthorized — session token missing. Try signing out and back in.");
      }
      const headers = new Headers(init?.headers);
      if (!headers.has("Content-Type") && init?.body) {
        headers.set("Content-Type", "application/json");
      }
      headers.set("Authorization", `Bearer ${token}`);
      return fetch(`${getApiBaseUrl()}${path}`, { ...init, headers });
    },
    [getToken]
  );

  return { fetchWithAuth, isLoaded, isSignedIn };
}
