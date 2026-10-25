"use client";

import { parseJsonOrThrow } from "@/lib/api-client/http";
import { useApiClient } from "@/hooks/useApiClient";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

type Board = {
  id: string;
  title: string;
  isDeleted: boolean;
  purgeAt: string | null;
};

type BoardsResponse = { items: Board[] };

export function useBoardsQuery() {
  const { fetchWithAuth, isLoaded, isSignedIn } = useApiClient();

  return useQuery({
    queryKey: ["boards"],
    enabled: isLoaded && isSignedIn,
    queryFn: async () => {
      return parseJsonOrThrow<BoardsResponse>(await fetchWithAuth("/boards"));
    },
  });
}

export function useCreateBoardMutation() {
  const qc = useQueryClient();
  const { fetchWithAuth } = useApiClient();

  return useMutation({
    mutationFn: async (title: string) => {
      return parseJsonOrThrow<Board>(
        await fetchWithAuth("/boards", {
          method: "POST",
          body: JSON.stringify({ title }),
        })
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boards"] }),
  });
}

export function useDeleteBoardMutation() {
  const qc = useQueryClient();
  const { fetchWithAuth } = useApiClient();

  return useMutation({
    mutationFn: async (boardId: string) => {
      return parseJsonOrThrow<{ deleted: boolean; restoreUntil: string }>(
        await fetchWithAuth(`/boards/${boardId}`, { method: "DELETE" })
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boards"] }),
  });
}

export function useRestoreBoardMutation() {
  const qc = useQueryClient();
  const { fetchWithAuth } = useApiClient();

  return useMutation({
    mutationFn: async (boardId: string) => {
      return parseJsonOrThrow<Board>(
        await fetchWithAuth(`/boards/${boardId}/restore`, { method: "POST" })
      );
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boards"] }),
  });
}
