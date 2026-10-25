"use client";

import { useDeleteBoardMutation, useRestoreBoardMutation } from "@/hooks/useBoardsQuery";
import { Trash2, RotateCcw, Loader2 } from "lucide-react";

type Props = {
  boardId: string;
  isDeleted: boolean;
  purgeAt: string | null;
};

export function BoardActions({ boardId, isDeleted, purgeAt }: Props) {
  const deleteMutation = useDeleteBoardMutation();
  const restoreMutation = useRestoreBoardMutation();

  if (isDeleted) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="text-[11px] text-amber-600 font-medium bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200/60">
          Trashed until {purgeAt ? new Date(purgeAt).toLocaleDateString() : "auto-purge"}
        </span>
        <button
          className="inline-flex items-center gap-1 rounded-xl bg-emerald-600 px-2.5 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-emerald-700 active:scale-[0.98] transition-all disabled:opacity-50"
          disabled={restoreMutation.isPending}
          onClick={() => restoreMutation.mutate(boardId)}
          type="button"
        >
          {restoreMutation.isPending ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <RotateCcw className="h-3 w-3" />
          )}
          <span>Restore</span>
        </button>
      </div>
    );
  }

  return (
    <button
      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 active:scale-[0.98] transition-all disabled:opacity-50"
      disabled={deleteMutation.isPending}
      onClick={() => deleteMutation.mutate(boardId)}
      title="Delete board"
      type="button"
    >
      {deleteMutation.isPending ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin text-rose-500" />
      ) : (
        <Trash2 className="h-3.5 w-3.5" />
      )}
      <span>Delete</span>
    </button>
  );
}
