"use client";

import { sanitizeAppState } from "@/lib/excalidraw/sanitize-app-state";
import dynamic from "next/dynamic";
import { useCallback, useRef } from "react";

type ExcalidrawImperativeAPI = {
  updateScene: (scene: Record<string, unknown>) => void;
  getSceneElements: () => readonly unknown[];
  getAppState: () => Record<string, unknown>;
  getFiles: () => Record<string, unknown>;
};

const Excalidraw = dynamic(async () => (await import("@excalidraw/excalidraw")).Excalidraw, {
  ssr: false,
});

export type ExcalidrawApiHandle = ExcalidrawImperativeAPI;

export function ExcalidrawCanvas({
  initialData,
  onSceneChange,
  onApiReady,
}: {
  initialData?: Record<string, unknown>;
  onSceneChange: (scene: Record<string, unknown>) => void;
  onApiReady?: (api: ExcalidrawApiHandle | null) => void;
}) {
  const apiRef = useRef<ExcalidrawApiHandle | null>(null);

  const handleApi = useCallback(
    (api: ExcalidrawApiHandle) => {
      apiRef.current = api;
      onApiReady?.(api);
    },
    [onApiReady]
  );

  return (
    <div className="h-full w-full">
      <Excalidraw
        initialData={initialData as never}
        excalidrawAPI={handleApi as never}
        onChange={(elements, appState, files) => {
          onSceneChange({
            elements,
            appState: sanitizeAppState(appState),
            files,
          });
        }}
      />
    </div>
  );
}
