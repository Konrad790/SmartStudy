"use client";

import { ExcalidrawCanvas, type ExcalidrawApiHandle } from "@/components/whiteboard/excalidraw-canvas";
import { DrawProposalBar } from "@/components/whiteboard/draw-proposal-bar";
import { AssistantSidebar } from "@/components/sidebar/assistant-sidebar";
import { StaleStateBanner } from "@/components/whiteboard/stale-state-banner";
import { useBoardAutosave } from "@/hooks/useBoardAutosave";
import { useApiClient } from "@/hooks/useApiClient";
import { useAssistantDraw } from "@/hooks/useAssistantDraw";
import type { TodrawPlan } from "@/hooks/useAssistantChat";
import { exportBoardImageFromScene } from "@/lib/excalidraw/export-board-image";
import {
  asAcceptedElements,
  asProposalElements,
  collectElementBboxes,
  isProposalElement,
  stripProposalElements,
  type ExcalidrawLikeElement,
} from "@/lib/excalidraw/proposal-elements";
import { sanitizeAppState } from "@/lib/excalidraw/sanitize-app-state";
import { useBoardVisionSync } from "@/hooks/useBoardVisionSync";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Sparkles, Loader2 } from "lucide-react";

async function toExcalidrawElements(
  elements: Array<Record<string, unknown>>
): Promise<ExcalidrawLikeElement[]> {
  try {
    const mod = await import("@excalidraw/excalidraw");
    if (typeof mod.convertToExcalidrawElements === "function") {
      return mod.convertToExcalidrawElements(elements as never) as unknown as ExcalidrawLikeElement[];
    }
  } catch {
    // fall through — use raw elements
  }
  return elements as ExcalidrawLikeElement[];
}

const emptyScene = (): Record<string, unknown> => ({
  elements: [],
  appState: sanitizeAppState({}),
  files: {},
});

function normalizeScene(raw: Record<string, unknown> | null | undefined): Record<string, unknown> {
  if (!raw || typeof raw !== "object") return emptyScene();
  return {
    elements: Array.isArray(raw.elements) ? raw.elements : [],
    appState: sanitizeAppState(raw.appState),
    files: typeof raw.files === "object" && raw.files !== null ? raw.files : {},
  };
}

/**
 * Fast O(N) scene signature computed solely over element versions and basic view state.
 * Avoids allocating and serializing multi-megabyte JSON strings on every pointer frame.
 */
function getSceneVersionSignature(
  elements: readonly unknown[],
  appState?: Record<string, unknown>
): string {
  let versionSum = 0;
  let deletedCount = 0;
  for (let i = 0; i < elements.length; i++) {
    const el = elements[i] as { version?: number; isDeleted?: boolean } | null;
    if (el) {
      if (el.isDeleted) deletedCount++;
      versionSum = (versionSum + (el.version ?? 0)) | 0;
    }
  }
  const bg = typeof appState?.viewBackgroundColor === "string" ? appState.viewBackgroundColor : "";
  const zoom =
    typeof appState?.zoom === "object" && appState.zoom
      ? (appState.zoom as { value?: number }).value ?? 1
      : 1;
  return `${elements.length}:${deletedCount}:${versionSum}:${bg}:${zoom}`;
}

export function BoardWorkspace({ boardId }: { boardId: string }) {
  const [showAssistant, setShowAssistant] = useState(false);
  const [assistantWidth, setAssistantWidth] = useState(420);
  const [assistantHeight, setAssistantHeight] = useState(560);
  const [isResizingWidth, setIsResizingWidth] = useState(false);
  const [isResizingHeight, setIsResizingHeight] = useState(false);
  const [sceneJson, setSceneJson] = useState<Record<string, unknown>>({});
  const [initialData, setInitialData] = useState<Record<string, unknown> | undefined>(undefined);
  const [snapshotReady, setSnapshotReady] = useState(false);
  const [pendingProposal, setPendingProposal] = useState<ExcalidrawLikeElement[] | null>(null);
  const [proposalSummary, setProposalSummary] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<Record<string, unknown>>({});
  const lastVersionSignatureRef = useRef("");
  const sceneDebounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pendingProposalRef = useRef<ExcalidrawLikeElement[] | null>(null);
  const apiRef = useRef<ExcalidrawApiHandle | null>(null);

  const getLatestScene = useCallback(() => {
    return sceneRef.current;
  }, []);

  const { fetchWithAuth, isLoaded, isSignedIn } = useApiClient();
  const { version, staleWarning } = useBoardAutosave(boardId, sceneJson, getLatestScene);
  const draw = useAssistantDraw(boardId);
  const { syncStatus, prepareBoardContextForPrompt } = useBoardVisionSync(
    boardId,
    sceneJson,
    snapshotReady && Boolean(isSignedIn),
    getLatestScene
  );

  const captureBoardImage = useCallback(async () => {
    const scene = sceneRef.current;
    const rawElements = Array.isArray(scene.elements) ? (scene.elements as unknown[]) : [];
    const elements = pendingProposalRef.current?.length
      ? stripProposalElements(rawElements)
      : rawElements;
    return exportBoardImageFromScene({ ...scene, elements });
  }, []);

  const handleApiReady = useCallback((api: ExcalidrawApiHandle | null) => {
    apiRef.current = api;
  }, []);

  const applySceneElements = useCallback((elements: ExcalidrawLikeElement[]) => {
    const api = apiRef.current;
    if (!api) return;
    api.updateScene({ elements });
  }, []);

  const handleSceneChange = useCallback(
    (nextScene: Record<string, unknown>) => {
      const rawElements = Array.isArray(nextScene.elements) ? nextScene.elements : [];
      const committed = pendingProposalRef.current?.length
        ? stripProposalElements(rawElements)
        : (rawElements as ExcalidrawLikeElement[]);
      const sanitized = {
        ...nextScene,
        elements: committed,
        appState: sanitizeAppState(nextScene.appState),
      };

      // 1. Immediate ref update: zero latency, zero React re-renders during active drawing
      sceneRef.current = sanitized;

      // 2. Debounce React state update and autosave/vision timers
      if (sceneDebounceTimerRef.current) {
        clearTimeout(sceneDebounceTimerRef.current);
      }

      sceneDebounceTimerRef.current = setTimeout(() => {
        const nextSig = getSceneVersionSignature(
          committed,
          nextScene.appState as Record<string, unknown>
        );
        if (nextSig === lastVersionSignatureRef.current) return;
        lastVersionSignatureRef.current = nextSig;
        setSceneJson(sanitized);
      }, 250);
    },
    []
  );

  const handleTodraw = useCallback(
    async (
      todraw: TodrawPlan,
      meta?: { boardContextJson?: Record<string, unknown> | null; visibleViewport?: Record<string, unknown> | null }
    ) => {
      const scene = sceneRef.current;
      const elements = Array.isArray(scene.elements) ? (scene.elements as unknown[]) : [];
      const summary =
        typeof todraw.summary === "string" && todraw.summary.trim() ? todraw.summary.trim() : null;
      setProposalSummary(summary);

      try {
        const result = await draw.mutateAsync({
          todraw,
          visibleViewport: (meta?.visibleViewport as never) ?? null,
          boardContextJson: meta?.boardContextJson ?? null,
          existingElementBboxes: collectElementBboxes(elements),
        });
        if (!result.elements.length) {
          setPendingProposal(null);
          pendingProposalRef.current = null;
          setProposalSummary(null);
          return;
        }
        const normalized = await toExcalidrawElements(result.elements);
        const proposal = asProposalElements(normalized);
        setPendingProposal(proposal);
        pendingProposalRef.current = proposal;
        const committed = stripProposalElements(elements);
        applySceneElements([...committed, ...proposal]);
      } catch {
        setPendingProposal(null);
        pendingProposalRef.current = null;
        setProposalSummary(null);
        throw new Error("Failed to prepare drawing suggestion.");
      }
    },
    [applySceneElements, draw]
  );

  const acceptProposal = useCallback(() => {
    if (!pendingProposal?.length) return;
    const scene = sceneRef.current;
    const elements = Array.isArray(scene.elements) ? (scene.elements as unknown[]) : [];
    const committed = stripProposalElements(elements);
    const accepted = asAcceptedElements(pendingProposal);
    const nextElements = [...committed, ...accepted];
    applySceneElements(nextElements);
    setPendingProposal(null);
    pendingProposalRef.current = null;
    setProposalSummary(null);
    const nextScene = {
      ...scene,
      elements: nextElements,
      appState: sanitizeAppState(scene.appState),
    };
    sceneRef.current = nextScene;
    lastVersionSignatureRef.current = getSceneVersionSignature(
      nextElements,
      nextScene.appState as Record<string, unknown>
    );
    setSceneJson(nextScene);
  }, [applySceneElements, pendingProposal]);

  const rejectProposal = useCallback(() => {
    const scene = sceneRef.current;
    const elements = Array.isArray(scene.elements) ? (scene.elements as unknown[]) : [];
    const committed = stripProposalElements(elements);
    const apiElements = apiRef.current?.getSceneElements() ?? [];
    const liveCommitted = (apiElements as ExcalidrawLikeElement[]).filter((el) => !isProposalElement(el));
    applySceneElements(liveCommitted.length ? liveCommitted : committed);
    setPendingProposal(null);
    pendingProposalRef.current = null;
    setProposalSummary(null);
  }, [applySceneElements]);

  useEffect(() => {
    return () => {
      if (sceneDebounceTimerRef.current) {
        clearTimeout(sceneDebounceTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    let cancelled = false;
    setSnapshotReady(false);
    setInitialData(undefined);
    setSceneJson({});
    sceneRef.current = {};
    setPendingProposal(null);
    pendingProposalRef.current = null;
    setProposalSummary(null);
    lastVersionSignatureRef.current = "";

    const loadSnapshot = async () => {
      const response = await fetchWithAuth(`/boards/${boardId}/snapshot`);
      if (cancelled) return;

      if (response.status === 404 || !response.ok) {
        const next = emptyScene();
        sceneRef.current = next;
        lastVersionSignatureRef.current = getSceneVersionSignature(
          [],
          next.appState as Record<string, unknown>
        );
        setInitialData(next);
        setSceneJson(next);
        setSnapshotReady(true);
        return;
      }

      const row = (await response.json()) as { sceneJson?: Record<string, unknown> };
      const next = normalizeScene(row.sceneJson);
      sceneRef.current = next;
      const rawElements = Array.isArray(next.elements) ? next.elements : [];
      lastVersionSignatureRef.current = getSceneVersionSignature(
        rawElements,
        next.appState as Record<string, unknown>
      );
      setInitialData(next);
      setSceneJson(next);
      setSnapshotReady(true);
    };

    void loadSnapshot();
    return () => {
      cancelled = true;
    };
  }, [boardId, fetchWithAuth, isLoaded, isSignedIn]);

  useEffect(() => {
    const onMove = (event: MouseEvent) => {
      if (!panelRef.current) return;
      const rect = panelRef.current.getBoundingClientRect();

      if (isResizingWidth) {
        const nextWidth = Math.max(320, Math.min(900, rect.right - event.clientX));
        setAssistantWidth(nextWidth);
      }

      if (isResizingHeight) {
        const nextHeight = Math.max(260, Math.min(window.innerHeight - 100, event.clientY - rect.top));
        setAssistantHeight(nextHeight);
      }
    };

    const stopResize = () => {
      setIsResizingWidth(false);
      setIsResizingHeight(false);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", stopResize);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", stopResize);
    };
  }, [isResizingWidth, isResizingHeight]);

  const showProposalUi = Boolean(pendingProposal?.length) || draw.isPending;

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-white select-none">
      {/* Top Floating Header Dock */}
      <header className="pointer-events-none absolute left-4 right-4 top-4 z-20 flex items-center justify-between">
        {/* Left Island: Back link, Title, Version badge, Stale warning */}
        <div className="pointer-events-auto flex items-center gap-2">
          <div className="flex items-center gap-2.5 rounded-2xl border border-slate-200/80 bg-white/90 px-3.5 py-2 shadow-sm backdrop-blur-md">
            <Link
              href="/boards"
              className="flex items-center gap-1.5 rounded-lg p-1 text-slate-500 hover:bg-slate-100 hover:text-indigo-600 transition-colors"
              title="Back to all boards"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>

            <div className="h-4 w-px bg-slate-200" />

            <div className="flex items-center gap-2">
              <div className="flex h-5 w-5 items-center justify-center rounded-md bg-indigo-50 text-indigo-600">
                <Sparkles className="h-3 w-3" />
              </div>
              <h1 className="text-xs font-semibold text-slate-800 tracking-tight">
                Whiteboard Workspace
              </h1>
            </div>

            <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[10px] font-medium text-slate-500 border border-slate-200/60">
              v{version}
            </span>
          </div>

          <StaleStateBanner show={staleWarning} />
        </div>

        {/* Right Island: Agent Toggle Button */}
        <div className="pointer-events-auto flex items-center gap-2">
          <button
            className={`flex items-center gap-2 rounded-2xl px-3.5 py-2 text-xs font-medium shadow-sm transition-all active:scale-[0.98] ${
              showAssistant
                ? "bg-indigo-600 text-white shadow-indigo-500/25 ring-2 ring-indigo-400/40 hover:bg-indigo-700"
                : "border border-slate-200/80 bg-white/90 text-slate-700 hover:bg-slate-50 hover:text-indigo-600 backdrop-blur-md"
            }`}
            onClick={() => setShowAssistant((v) => !v)}
            type="button"
          >
            <Sparkles className={`h-3.5 w-3.5 ${showAssistant ? "text-indigo-200" : "text-indigo-500"}`} />
            <span>{showAssistant ? "Hide agent" : "Show agent"}</span>
          </button>
        </div>
      </header>

      {/* Floating Draw Proposal Notification */}
      {showProposalUi ? (
        <div className="absolute left-4 top-16 z-20">
          <DrawProposalBar
            isDrawing={draw.isPending}
            onAccept={acceptProposal}
            onReject={rejectProposal}
            summary={proposalSummary}
          />
        </div>
      ) : null}

      {/* Excalidraw Full Screen Canvas — Edge to Edge without borders */}
      {snapshotReady ? (
        <ExcalidrawCanvas
          key={boardId}
          initialData={initialData ?? emptyScene()}
          onApiReady={handleApiReady}
          onSceneChange={handleSceneChange}
        />
      ) : (
        <div className="flex h-full w-full flex-col items-center justify-center gap-2.5 bg-slate-50 text-xs text-slate-500">
          <Loader2 className="h-6 w-6 animate-spin text-indigo-600" />
          <span>Loading whiteboard canvas…</span>
        </div>
      )}

      {/* Floating AI Assistant Panel */}
      {showAssistant ? (
        <div
          className="absolute right-4 top-16 z-30 overflow-hidden rounded-2xl shadow-2xl"
          ref={panelRef}
          style={{ width: assistantWidth, height: assistantHeight }}
        >
          {/* Left Resize Handle */}
          <button
            aria-label="Resize agent width"
            className="group absolute bottom-0 left-0 top-0 z-40 w-2.5 cursor-ew-resize bg-transparent hover:bg-indigo-400/30 transition-colors"
            onMouseDown={() => setIsResizingWidth(true)}
            type="button"
          />

          {/* Bottom Resize Handle */}
          <button
            aria-label="Resize agent height"
            className="group absolute bottom-0 left-0 right-0 z-40 h-2.5 cursor-ns-resize bg-transparent hover:bg-indigo-400/30 transition-colors"
            onMouseDown={() => setIsResizingHeight(true)}
            type="button"
          />

          <AssistantSidebar
            boardId={boardId}
            captureBoardImage={captureBoardImage}
            prepareBoardContext={prepareBoardContextForPrompt}
            syncStatus={syncStatus}
            onClose={() => setShowAssistant(false)}
            className="h-full w-full overflow-hidden"
            onTodraw={handleTodraw}
          />
        </div>
      ) : null}
    </main>
  );
}
