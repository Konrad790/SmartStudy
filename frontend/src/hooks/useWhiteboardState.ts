"use client";

import { useMemo, useState } from "react";

export function useWhiteboardState() {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const viewport = useMemo(() => ({ zoom, pan }), [zoom, pan]);
  return { viewport, setZoom, setPan };
}
