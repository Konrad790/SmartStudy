"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  exportBoardPatchFromScene,
  readVisibleViewportFromScene,
  type BoundingBox,
  type VisibleViewport,
} from "@/lib/excalidraw/export-board-image";
import { stripProposalElements } from "@/lib/excalidraw/proposal-elements";
import { useVisionSync } from "@/hooks/useVisionSync";

/** Delay after drawing ends before evaluating background sync (3 seconds). */
const IDLE_DEBOUNCE_MS = 3000;

/** Minimum interval between background AI vision checks (2 minutes). */
const BACKGROUND_COOLDOWN_MS = 2 * 60 * 1000;

export type VisionSyncStatus = "idle" | "cooldown" | "syncing" | "synced" | "error";

export type PreparedBoardContext = {
  boardImageMimeType?: "image/png";
  boardImageBase64?: string;
  patchBbox?: BoundingBox | null;
  visibleViewport?: VisibleViewport | null;
  hasChanges: boolean;
};

type CleanElement = {
  id: string;
  version: number;
  isDeleted?: boolean;
  [key: string]: unknown;
};

function isCleanElement(el: unknown): el is CleanElement {
  return (
    typeof el === "object" &&
    el !== null &&
    typeof (el as Record<string, unknown>).id === "string" &&
    typeof (el as Record<string, unknown>).version === "number" &&
    Boolean((el as Record<string, unknown>).id) &&
    !(el as Record<string, unknown>).isDeleted
  );
}

export function useBoardVisionSync(
  boardId: string,
  sceneJson: Record<string, unknown>,
  enabled = true,
  getLatestScene?: () => Record<string, unknown>
) {
  const visionSync = useVisionSync(boardId);

  const [syncStatus, setSyncStatus] = useState<VisionSyncStatus>("idle");
  const [lastSyncedAt, setLastSyncedAt] = useState<number | null>(null);

  const lastCheckTimeRef = useRef<number>(0);
  const lastAnalyzedVersionsRef = useRef<Map<string, number>>(new Map());
  const isSyncingRef = useRef<boolean>(false);
  const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
  const cooldownTimerRef = useRef<NodeJS.Timeout | null>(null);
  const sceneJsonRef = useRef(sceneJson);
  const getLatestSceneRef = useRef(getLatestScene);

  sceneJsonRef.current = sceneJson;
  getLatestSceneRef.current = getLatestScene;

  const getChangedElements = useCallback(() => {
    const scene = getLatestSceneRef.current ? getLatestSceneRef.current() : sceneJsonRef.current;
    const rawElements = Array.isArray(scene.elements) ? scene.elements : [];
    const stripped = stripProposalElements(rawElements as unknown[]);
    const committed: CleanElement[] = stripped.filter(isCleanElement);

    const changed = committed.filter((el) => {
      const lastVersion = lastAnalyzedVersionsRef.current.get(el.id);
      return lastVersion === undefined || el.version > lastVersion;
    });

    return { committed, changed };
  }, []);

  const runBackgroundSync = useCallback(async () => {
    if (!enabled || isSyncingRef.current) return;

    const { committed, changed } = getChangedElements();
    if (committed.length === 0 || changed.length === 0) {
      return;
    }

    isSyncingRef.current = true;
    setSyncStatus("syncing");

    try {
      const changedIds = changed.map((el) => el.id);
      const scene = getLatestSceneRef.current ? getLatestSceneRef.current() : sceneJsonRef.current;
      const patch = await exportBoardPatchFromScene(scene, changedIds);

      if (!patch) {
        setSyncStatus("idle");
        isSyncingRef.current = false;
        return;
      }

      await visionSync.mutateAsync({
        boardImageMimeType: patch.boardImageMimeType,
        boardImageBase64: patch.boardImageBase64,
        patchBbox: patch.patchBbox,
        visibleViewport: patch.visibleViewport,
      });

      lastCheckTimeRef.current = Date.now();
      for (const el of committed) {
        lastAnalyzedVersionsRef.current.set(el.id, el.version);
      }

      setLastSyncedAt(Date.now());
      setSyncStatus("synced");
    } catch {
      setSyncStatus("error");
    } finally {
      isSyncingRef.current = false;
    }
  }, [enabled, getChangedElements, visionSync]);

  // Main listener for scene element changes
  useEffect(() => {
    if (!enabled) return;

    const { committed, changed } = getChangedElements();
    if (committed.length === 0 || changed.length === 0) {
      return;
    }

    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
    }
    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
    }

    idleTimerRef.current = setTimeout(() => {
      const now = Date.now();
      const elapsed = now - lastCheckTimeRef.current;
      const isInitial = lastCheckTimeRef.current === 0;

      if (isInitial || elapsed >= BACKGROUND_COOLDOWN_MS) {
        void runBackgroundSync();
      } else {
        setSyncStatus("cooldown");
        const remaining = BACKGROUND_COOLDOWN_MS - elapsed;
        cooldownTimerRef.current = setTimeout(() => {
          void runBackgroundSync();
        }, remaining);
      }
    }, IDLE_DEBOUNCE_MS);

    return () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
    };
  }, [enabled, getChangedElements, runBackgroundSync, sceneJson.elements]);

  /**
   * Called immediately when user sends a prompt in the chat.
   * If there are unanalyzed changes or board was never scanned, captures high-res crop
   * immediately without waiting for cooldown. If already synced, returns cached state without image.
   */
  const prepareBoardContextForPrompt = useCallback(async (): Promise<PreparedBoardContext> => {
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);

    const { committed, changed } = getChangedElements();
    if (committed.length === 0) {
      return { hasChanges: false, visibleViewport: null };
    }

    const isInitial = lastCheckTimeRef.current === 0;

    if (changed.length > 0 || isInitial) {
      setSyncStatus("syncing");
      const changedIds = isInitial ? null : changed.map((el) => el.id);
      const scene = getLatestSceneRef.current ? getLatestSceneRef.current() : sceneJsonRef.current;
      const patch = await exportBoardPatchFromScene(scene, changedIds);

      if (patch) {
        lastCheckTimeRef.current = Date.now();
        for (const el of committed) {
          lastAnalyzedVersionsRef.current.set(el.id, el.version);
        }
        setLastSyncedAt(Date.now());
        setSyncStatus("synced");

        return {
          boardImageMimeType: patch.boardImageMimeType,
          boardImageBase64: patch.boardImageBase64,
          patchBbox: patch.patchBbox,
          visibleViewport: patch.visibleViewport,
          hasChanges: true,
        };
      }
    }

    // No changes on board — existing context is up-to-date!
    const scene = getLatestSceneRef.current ? getLatestSceneRef.current() : sceneJsonRef.current;
    const viewport = await readVisibleViewportFromScene(scene);
    return {
      visibleViewport: viewport,
      hasChanges: false,
    };
  }, [getChangedElements]);

  return {
    syncStatus,
    lastSyncedAt,
    prepareBoardContextForPrompt,
  };
}
