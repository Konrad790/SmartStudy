import { sanitizeAppState } from "@/lib/excalidraw/sanitize-app-state";
import { normalizeBase64ImagePayload } from "@/lib/utils/base64-image";

/** Keeps payloads small for Gemini free tier and JSON body limits. */
const MAX_EXPORT_DIMENSION = 1280;

export type VisibleViewport = {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  zoom: number;
  widthPx: number;
  heightPx: number;
};

export type BoundingBox = {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
};

export type BoardImagePayload = {
  boardImageMimeType: "image/png";
  boardImageBase64: string;
  visibleViewport: VisibleViewport | null;
};

export type BoardPatchPayload = {
  boardImageMimeType: "image/png";
  boardImageBase64: string;
  patchBbox: BoundingBox;
  isFullBoard: boolean;
  visibleViewport: VisibleViewport | null;
  elementIds: string[];
};

export function getElementBounds(el: {
  x: number;
  y: number;
  width: number;
  height: number;
}): BoundingBox {
  const minX = Math.min(el.x, el.x + el.width);
  const maxX = Math.max(el.x, el.x + el.width);
  const minY = Math.min(el.y, el.y + el.height);
  const maxY = Math.max(el.y, el.y + el.height);
  return {
    minX,
    minY,
    maxX,
    maxY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}

export function unionBounds(boxes: BoundingBox[]): BoundingBox | null {
  if (boxes.length === 0) return null;
  let minX = boxes[0].minX;
  let minY = boxes[0].minY;
  let maxX = boxes[0].maxX;
  let maxY = boxes[0].maxY;
  for (let i = 1; i < boxes.length; i++) {
    minX = Math.min(minX, boxes[i].minX);
    minY = Math.min(minY, boxes[i].minY);
    maxX = Math.max(maxX, boxes[i].maxX);
    maxY = Math.max(maxY, boxes[i].maxY);
  }
  return {
    minX,
    minY,
    maxX,
    maxY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}

export function boxesIntersect(a: BoundingBox, b: BoundingBox): boolean {
  return a.minX <= b.maxX && a.maxX >= b.minX && a.minY <= b.maxY && a.maxY >= b.minY;
}

function zoomValue(zoom: unknown): number {
  if (typeof zoom === "number" && zoom > 0) return zoom;
  if (zoom && typeof zoom === "object" && "value" in zoom) {
    const value = (zoom as { value: unknown }).value;
    if (typeof value === "number" && value > 0) return value;
  }
  return 1;
}

export function readVisibleViewport(
  appState: Record<string, unknown>,
  getVisibleSceneBounds: (state: never) => readonly [number, number, number, number]
): VisibleViewport | null {
  const width = typeof appState.width === "number" ? appState.width : 0;
  const height = typeof appState.height === "number" ? appState.height : 0;
  if (width <= 0 || height <= 0) return null;

  const zoom = zoomValue(appState.zoom);
  const scrollX = typeof appState.scrollX === "number" ? appState.scrollX : 0;
  const scrollY = typeof appState.scrollY === "number" ? appState.scrollY : 0;

  const [minX, minY, maxX, maxY] = getVisibleSceneBounds({
    scrollX,
    scrollY,
    width,
    height,
    zoom: { value: zoom },
  } as never);

  return {
    minX,
    minY,
    maxX,
    maxY,
    zoom,
    widthPx: width,
    heightPx: height,
  };
}

export async function readVisibleViewportFromScene(
  scene: Record<string, unknown>
): Promise<VisibleViewport | null> {
  const { getVisibleSceneBounds } = await import("@excalidraw/excalidraw");
  const appState = sanitizeAppState(scene.appState);
  return readVisibleViewport(appState, getVisibleSceneBounds);
}

export async function exportBoardImageFromScene(
  scene: Record<string, unknown>
): Promise<BoardImagePayload | null> {
  const elements = Array.isArray(scene.elements) ? scene.elements : [];
  if (elements.length === 0) {
    return null;
  }

  const { exportToBlob, getVisibleSceneBounds } = await import("@excalidraw/excalidraw");
  const appState = sanitizeAppState(scene.appState);
  const visibleViewport = readVisibleViewport(appState, getVisibleSceneBounds);

  const blob = await exportToBlob({
    elements: elements as never,
    appState: {
      ...appState,
      exportWithDarkMode: false,
      exportBackground: true,
    } as never,
    files: (typeof scene.files === "object" && scene.files !== null ? scene.files : {}) as never,
    mimeType: "image/png",
    quality: 0.85,
    maxWidthOrHeight: MAX_EXPORT_DIMENSION,
  });

  const dataUrl = await readBlobAsDataUrl(blob);
  return {
    boardImageMimeType: "image/png",
    boardImageBase64: normalizeBase64ImagePayload(dataUrl),
    visibleViewport,
  };
}

export async function exportBoardPatchFromScene(
  scene: Record<string, unknown>,
  targetElementIds?: string[] | null,
  padding = 50
): Promise<BoardPatchPayload | null> {
  const allElements = Array.isArray(scene.elements)
    ? (scene.elements as Array<Record<string, unknown>>)
    : [];
  const validElements = allElements.filter((el) => el && typeof el === "object" && !el.isDeleted);
  if (validElements.length === 0) {
    return null;
  }

  const { exportToBlob, getVisibleSceneBounds } = await import("@excalidraw/excalidraw");
  const appState = sanitizeAppState(scene.appState);
  const visibleViewport = readVisibleViewport(appState, getVisibleSceneBounds);

  let exportElements: Array<Record<string, unknown>> = validElements;
  let patchBbox: BoundingBox = { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
  let isFullBoard = true;

  if (targetElementIds && targetElementIds.length > 0) {
    const targetSet = new Set(targetElementIds);
    const matchedTargets = validElements.filter(
      (el) => typeof el.id === "string" && targetSet.has(el.id)
    );

    if (matchedTargets.length > 0) {
      const targetBoxes = matchedTargets.map((el) =>
        getElementBounds(el as { x: number; y: number; width: number; height: number })
      );
      const rawTargetBox = unionBounds(targetBoxes);
      if (rawTargetBox) {
        patchBbox = {
          minX: Math.round(rawTargetBox.minX),
          minY: Math.round(rawTargetBox.minY),
          maxX: Math.round(rawTargetBox.maxX),
          maxY: Math.round(rawTargetBox.maxY),
          width: Math.round(rawTargetBox.width),
          height: Math.round(rawTargetBox.height),
        };
        const paddedBox: BoundingBox = {
          minX: rawTargetBox.minX - padding,
          minY: rawTargetBox.minY - padding,
          maxX: rawTargetBox.maxX + padding,
          maxY: rawTargetBox.maxY + padding,
          width: rawTargetBox.width + 2 * padding,
          height: rawTargetBox.height + 2 * padding,
        };

        // Include all nearby or intersecting elements for spatial context
        exportElements = validElements.filter((el) => {
          const b = getElementBounds(el as { x: number; y: number; width: number; height: number });
          return boxesIntersect(b, paddedBox);
        });
        isFullBoard = false;
      }
    }
  }

  if (isFullBoard) {
    const allBoxes = validElements.map((el) =>
      getElementBounds(el as { x: number; y: number; width: number; height: number })
    );
    const rawBox = unionBounds(allBoxes) ?? {
      minX: 0,
      minY: 0,
      maxX: 100,
      maxY: 100,
      width: 100,
      height: 100,
    };
    patchBbox = {
      minX: Math.round(rawBox.minX),
      minY: Math.round(rawBox.minY),
      maxX: Math.round(rawBox.maxX),
      maxY: Math.round(rawBox.maxY),
      width: Math.round(rawBox.width),
      height: Math.round(rawBox.height),
    };
  }

  // Focused patch stays at high resolution without heavy downscaling
  const maxDim = isFullBoard ? MAX_EXPORT_DIMENSION : 1920;

  const blob = await exportToBlob({
    elements: exportElements as never,
    appState: {
      ...appState,
      exportWithDarkMode: false,
      exportBackground: true,
      exportPadding: 20,
    } as never,
    files: (typeof scene.files === "object" && scene.files !== null ? scene.files : {}) as never,
    mimeType: "image/png",
    quality: 0.9,
    maxWidthOrHeight: maxDim,
  });

  const dataUrl = await readBlobAsDataUrl(blob);
  return {
    boardImageMimeType: "image/png",
    boardImageBase64: normalizeBase64ImagePayload(dataUrl),
    patchBbox,
    isFullBoard,
    visibleViewport,
    elementIds: exportElements.map((el) => String(el.id)),
  };
}

function readBlobAsDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result !== "string") {
        reject(new Error("Failed to encode board screenshot"));
        return;
      }
      resolve(reader.result);
    };
    reader.onerror = () => reject(reader.error ?? new Error("Failed to read board screenshot"));
    reader.readAsDataURL(blob);
  });
}
