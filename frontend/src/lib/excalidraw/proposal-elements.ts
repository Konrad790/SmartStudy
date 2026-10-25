/** Marker used to identify pending tutor draw proposals on the canvas. */
export const PROPOSAL_CUSTOM_DATA_KEY = "smartstudyProposal";

export type ExcalidrawLikeElement = Record<string, unknown> & {
  id?: string;
  isDeleted?: boolean;
  opacity?: number;
  strokeStyle?: string;
  customData?: Record<string, unknown> | null;
};

export function isProposalElement(element: ExcalidrawLikeElement): boolean {
  const custom = element.customData;
  return Boolean(custom && custom[PROPOSAL_CUSTOM_DATA_KEY] === true);
}

export function elementId(element: ExcalidrawLikeElement, index: number): string {
  if (typeof element.id === "string" && element.id.trim()) return element.id;
  return `ss-draw-${Date.now()}-${index}`;
}

/** Style proposed elements so they read as a preview (Cursor-like suggestion). */
export function asProposalElements(
  elements: Array<Record<string, unknown>>
): ExcalidrawLikeElement[] {
  return elements.map((raw, index) => {
    const id = elementId(raw, index);
    const existingCustom =
      raw.customData && typeof raw.customData === "object" && !Array.isArray(raw.customData)
        ? (raw.customData as Record<string, unknown>)
        : {};
    return {
      ...raw,
      id,
      opacity: typeof raw.opacity === "number" ? Math.min(raw.opacity, 55) : 55,
      strokeStyle: typeof raw.strokeStyle === "string" ? raw.strokeStyle : "dashed",
      locked: true,
      customData: {
        ...existingCustom,
        [PROPOSAL_CUSTOM_DATA_KEY]: true,
      },
    };
  });
}

/** Commit proposal styling to normal board elements. */
export function asAcceptedElements(elements: ExcalidrawLikeElement[]): ExcalidrawLikeElement[] {
  return elements.map((el) => {
    const custom = { ...(el.customData ?? {}) };
    delete custom[PROPOSAL_CUSTOM_DATA_KEY];
    return {
      ...el,
      opacity: 100,
      strokeStyle: "solid",
      locked: false,
      customData: Object.keys(custom).length > 0 ? custom : null,
    };
  });
}

export function stripProposalElements(elements: unknown[]): ExcalidrawLikeElement[] {
  return (elements as ExcalidrawLikeElement[]).filter((el) => !isProposalElement(el));
}

export function collectElementBboxes(elements: unknown[]): Array<{
  id?: string;
  x: number;
  y: number;
  width: number;
  height: number;
}> {
  const out: Array<{ id?: string; x: number; y: number; width: number; height: number }> = [];
  for (const raw of elements) {
    if (!raw || typeof raw !== "object") continue;
    const el = raw as ExcalidrawLikeElement;
    if (el.isDeleted) continue;
    if (isProposalElement(el)) continue;
    const x = typeof el.x === "number" ? el.x : null;
    const y = typeof el.y === "number" ? el.y : null;
    const width = typeof el.width === "number" ? el.width : null;
    const height = typeof el.height === "number" ? el.height : null;
    if (x === null || y === null || width === null || height === null) continue;
    out.push({
      id: typeof el.id === "string" ? el.id : undefined,
      x,
      y,
      width,
      height,
    });
  }
  return out;
}
