"use client";

import { parseJsonOrThrow } from "@/lib/api-client/http";
import { useApiClient } from "@/hooks/useApiClient";
import { visionSyncSchema } from "@/lib/validation/assistant";
import { useMutation } from "@tanstack/react-query";

export type VisionSyncPayload = {
  boardImageMimeType: "image/png" | "image/jpeg" | "image/webp";
  boardImageBase64: string;
  patchBbox?: {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
    width: number;
    height: number;
  } | null;
  visibleViewport?: {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
    zoom: number;
    widthPx: number;
    heightPx: number;
  } | null;
};

export type VisionSyncResponse = {
  boardContextJson: Record<string, unknown>;
  status: string;
};

export function useVisionSync(boardId: string) {
  const { fetchWithAuth } = useApiClient();

  return useMutation({
    mutationFn: async (payload: VisionSyncPayload) => {
      const body = visionSyncSchema.parse(payload);
      return parseJsonOrThrow<VisionSyncResponse>(
        await fetchWithAuth(`/boards/${boardId}/assistant/vision-sync`, {
          method: "POST",
          body: JSON.stringify(body),
        })
      );
    },
  });
}
