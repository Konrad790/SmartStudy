"use client";

import { Check, X, Sparkles, Loader2 } from "lucide-react";

type Props = {
  summary?: string | null;
  isDrawing?: boolean;
  onAccept: () => void;
  onReject: () => void;
};

export function DrawProposalBar({ summary, isDrawing, onAccept, onReject }: Props) {
  if (isDrawing) {
    return (
      <div className="pointer-events-auto flex items-center gap-2.5 rounded-2xl border border-indigo-200/80 bg-white/95 px-4 py-2.5 text-xs font-medium text-indigo-900 shadow-xl shadow-indigo-500/10 backdrop-blur-md animate-pulse">
        <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
        <span>Preparing drawing suggestion…</span>
      </div>
    );
  }

  return (
    <div className="pointer-events-auto flex max-w-sm flex-col gap-2.5 rounded-2xl border border-indigo-100 bg-white/95 p-3.5 text-xs text-slate-800 shadow-xl shadow-indigo-500/10 backdrop-blur-md transition-all">
      <div className="flex items-center gap-1.5 font-semibold text-indigo-900">
        <div className="flex h-5 w-5 items-center justify-center rounded-md bg-indigo-50 text-indigo-600">
          <Sparkles className="h-3 w-3" />
        </div>
        <span>AI Drawing Suggestion</span>
      </div>

      {summary ? (
        <p className="text-slate-600 leading-relaxed font-normal bg-slate-50/80 p-2 rounded-lg border border-slate-100">
          {summary}
        </p>
      ) : null}

      <p className="text-[11px] text-slate-400">
        Preview is shown with dashed lines. Choose whether to keep it on your board.
      </p>

      <div className="flex items-center gap-2 pt-1">
        <button
          className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-xl bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-emerald-700 active:scale-[0.98] transition-all"
          onClick={onAccept}
          type="button"
        >
          <Check className="h-3.5 w-3.5" />
          Accept
        </button>
        <button
          className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 active:scale-[0.98] transition-all"
          onClick={onReject}
          type="button"
        >
          <X className="h-3.5 w-3.5" />
          Reject
        </button>
      </div>
    </div>
  );
}
