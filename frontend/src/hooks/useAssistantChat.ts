"use client";

import { parseJsonOrThrow } from "@/lib/api-client/http";
import { useApiClient } from "@/hooks/useApiClient";
import { assistantMessageSchema } from "@/lib/validation/assistant";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

export type AssistantChatPayload = {
  message: string;
  conversationId?: string | null;
  boardImageMimeType?: "image/png" | "image/jpeg" | "image/webp";
  boardImageBase64?: string;
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

export type TodrawPlan = {
  summary?: string;
  placement?: Record<string, unknown>;
  items?: Array<Record<string, unknown>>;
  [key: string]: unknown;
};

export type AssistantChatResponse = {
  message: string;
  conversationId?: string | null;
  boardContextJson?: Record<string, unknown> | null;
  todraw?: TodrawPlan | null;
};

export type AssistantStreamEvent =
  | { type: "status"; stage: string; message: string }
  | { type: "delta"; text: string }
  | {
      type: "done";
      message: string;
      conversationId?: string | null;
      boardContextJson?: Record<string, unknown> | null;
      todraw?: TodrawPlan | null;
    }
  | { type: "error"; error: string; service?: string };

export type StreamCallbacks = {
  onStatus?: (status: { stage: string; message: string }) => void;
  onDelta?: (delta: string) => void;
  onDone?: (response: AssistantChatResponse) => void;
  onError?: (error: Error) => void;
};

export type ConversationItem = {
  id: string;
  boardId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  lastMessagePreview?: string | null;
};

export type ConversationMessage = {
  id: string;
  conversationId: string | null;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
};

export function useAssistantChat(boardId: string) {
  const { fetchWithAuth } = useApiClient();

  const mutation = useMutation({
    mutationFn: async (payload: AssistantChatPayload) => {
      const body = assistantMessageSchema.parse(payload);
      return parseJsonOrThrow<AssistantChatResponse>(
        await fetchWithAuth(`/boards/${boardId}/assistant/chat`, {
          method: "POST",
          body: JSON.stringify(body),
        })
      );
    },
  });

  const streamChat = useCallback(
    async (
      payload: AssistantChatPayload,
      callbacks?: StreamCallbacks,
      signal?: AbortSignal
    ): Promise<AssistantChatResponse> => {
      const body = assistantMessageSchema.parse(payload);
      const response = await fetchWithAuth(`/boards/${boardId}/assistant/chat/stream`, {
        method: "POST",
        body: JSON.stringify(body),
        signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMsg = `Server error (${response.status})`;
        try {
          const parsed = JSON.parse(errorText);
          let msg = parsed.message;
          let srv = parsed.service;
          if (!msg && typeof parsed.detail === "string") {
            msg = parsed.detail;
          } else if (typeof parsed.detail === "object" && parsed.detail) {
            msg = msg ?? parsed.detail.message;
            srv = srv ?? parsed.detail.service;
          }
          if (msg) {
            errorMsg = srv && !msg.includes(srv) ? `[${srv}] ${msg}` : msg;
          }
        } catch {
          if (errorText) errorMsg = errorText;
        }
        const err = new Error(errorMsg);
        callbacks?.onError?.(err);
        throw err;
      }

      if (!response.body) {
        throw new Error("Response body is not readable");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let finalResponse: AssistantChatResponse | null = null;

      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            const lines = part.split("\n");
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed.startsWith("data:")) continue;
              const jsonStr = trimmed.slice(5).trim();
              if (!jsonStr) continue;

              let event: AssistantStreamEvent | null = null;
              try {
                event = JSON.parse(jsonStr) as AssistantStreamEvent;
                if (event.type === "status") {
                  callbacks?.onStatus?.({ stage: event.stage, message: event.message });
                } else if (event.type === "delta") {
                  callbacks?.onDelta?.(event.text);
                } else if (event.type === "done") {
                  finalResponse = {
                    message: event.message,
                    conversationId: event.conversationId,
                    boardContextJson: event.boardContextJson,
                    todraw: event.todraw,
                  };
                  callbacks?.onDone?.(finalResponse);
                } else if (event.type === "error") {
                  const srv = event.service;
                  const fullMsg = srv && !event.error.includes(srv) ? `[${srv}] ${event.error}` : event.error;
                  const err = new Error(fullMsg);
                  callbacks?.onError?.(err);
                  throw err;
                }
              } catch (err) {
                if (event && event.type === "error") {
                  throw err;
                }
                console.error("Failed to parse SSE event", err);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      if (!finalResponse) {
        throw new Error("Stream closed without final response.");
      }
      return finalResponse;
    },
    [boardId, fetchWithAuth]
  );

  return Object.assign(mutation, { streamChat });
}

export function useConversations(boardId: string) {
  const { fetchWithAuth } = useApiClient();
  const queryClient = useQueryClient();

  const queryKey = ["boards", boardId, "conversations"];

  const conversationsQuery = useQuery({
    queryKey,
    queryFn: async () => {
      const res = await fetchWithAuth(`/boards/${boardId}/assistant/conversations`);
      return parseJsonOrThrow<ConversationItem[]>(res);
    },
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const createMutation = useMutation({
    mutationFn: async (title?: string) => {
      const res = await fetchWithAuth(`/boards/${boardId}/assistant/conversations`, {
        method: "POST",
        body: JSON.stringify({ title }),
      });
      return parseJsonOrThrow<ConversationItem>(res);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (conversationId: string) => {
      const res = await fetchWithAuth(`/boards/${boardId}/assistant/conversations/${conversationId}`, {
        method: "DELETE",
      });
      return parseJsonOrThrow<{ status: string }>(res);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  const fetchMessages = useCallback(
    async (conversationId: string): Promise<ConversationMessage[]> => {
      const res = await fetchWithAuth(
        `/boards/${boardId}/assistant/conversations/${conversationId}/messages`
      );
      return parseJsonOrThrow<ConversationMessage[]>(res);
    },
    [boardId, fetchWithAuth]
  );

  return {
    conversations: conversationsQuery.data ?? [],
    isLoading: conversationsQuery.isLoading,
    refetch: conversationsQuery.refetch,
    createConversation: createMutation.mutateAsync,
    isCreating: createMutation.isPending,
    deleteConversation: deleteMutation.mutateAsync,
    isDeleting: deleteMutation.isPending,
    fetchMessages,
  };
}
