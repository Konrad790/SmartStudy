"use client";

import { useApiClient } from "@/hooks/useApiClient";
import { useCallback, useEffect, useRef, useState } from "react";

type Result = {
  staleWarning: boolean;
  version: number;
};

export function useBoardAutosave(
  boardId: string,
  sceneJson: Record<string, unknown>,
  getLatestScene?: () => Record<string, unknown>
) {
  const { fetchWithAuth, isLoaded, isSignedIn } = useApiClient();
  const [version, setVersion] = useState(0);
  const [staleWarning, setStaleWarning] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const versionRef = useRef(0);
  const sceneJsonRef = useRef<Record<string, unknown>>({});
  const getLatestSceneRef = useRef(getLatestScene);

  getLatestSceneRef.current = getLatestScene;

  useEffect(() => {
    sceneJsonRef.current = sceneJson;
  }, [sceneJson]);

  useEffect(() => {
    if (!boardId || !isLoaded || !isSignedIn) return;
    let cancelled = false;
    versionRef.current = 0;
    setVersion(0);

    const loadVersion = async () => {
      const response = await fetchWithAuth(`/boards/${boardId}/snapshot`);
      if (cancelled) return;
      if (response.status === 404) {
        versionRef.current = 0;
        setVersion(0);
        setStaleWarning(false);
        return;
      }
      if (!response.ok) return;
      const data = (await response.json()) as { version?: number };
      const nextVersion = data.version ?? 0;
      versionRef.current = nextVersion;
      setVersion(nextVersion);
      setStaleWarning(false);
    };

    void loadVersion();
    return () => {
      cancelled = true;
    };
  }, [boardId, fetchWithAuth, isLoaded, isSignedIn]);

  const persist = useCallback(
    async (body: Record<string, unknown>, baseVersion: number) => {
      const response = await fetchWithAuth(`/boards/${boardId}/snapshot`, {
        method: "PUT",
        body: JSON.stringify({ baseVersion, sceneJson: body }),
      });
      if (!response.ok) return;
      const data = (await response.json()) as Result;
      versionRef.current = data.version;
      setVersion(data.version);
      setStaleWarning(data.staleWarning);
    },
    [boardId, fetchWithAuth]
  );

  useEffect(() => {
    if (!boardId || !isSignedIn) return;
    if (!sceneJson || Object.keys(sceneJson).length === 0) return;
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      const current = getLatestSceneRef.current ? getLatestSceneRef.current() : sceneJson;
      void persist(current, versionRef.current);
    }, 800);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [boardId, sceneJson, persist, isSignedIn]);

  useEffect(() => {
    if (!boardId) return;

    const flushKeepalive = () => {
      const body = getLatestSceneRef.current ? getLatestSceneRef.current() : sceneJsonRef.current;
      if (!body || Object.keys(body).length === 0) return;
      void persist(body, versionRef.current);
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === "hidden") flushKeepalive();
    };

    window.addEventListener("pagehide", flushKeepalive);
    document.addEventListener("visibilitychange", onVisibilityChange);
    return () => {
      window.removeEventListener("pagehide", flushKeepalive);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [boardId, persist]);

  return { version, staleWarning };
}
