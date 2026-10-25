"use client";

import { parseJsonOrThrow } from "@/lib/api-client/http";
import { useApiClient } from "@/hooks/useApiClient";
import { assistantDrawSchema } from "@/lib/validation/assistant";
import type { TodrawPlan } from "@/hooks/useAssistantChat";
import { useMutation } from "@tanstack/react-query";

export type AssistantDrawPayload = {
  todraw: TodrawPlan;
  visibleViewport?: {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
    zoom: number;
    widthPx: number;
    heightPx: number;
  } | null;
  boardContextJson?: Record<string, unknown> | null;
  existingElementBboxes?: Array<{
    id?: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
};

export type AssistantDrawResponse = {
  elements: Array<Record<string, unknown>>;
  notes?: string | null;
};

export function useAssistantDraw(boardId: string) {
  const { fetchWithAuth } = useApiClient();

  return useMutation({
    mutationFn: async (payload: AssistantDrawPayload) => {
      const body = assistantDrawSchema.parse(payload);
      return parseJsonOrThrow<AssistantDrawResponse>(
        await fetchWithAuth(`/boards/${boardId}/assistant/draw`, {
          method: "POST",
          body: JSON.stringify(body),
        })
      );
    },
  });
}
