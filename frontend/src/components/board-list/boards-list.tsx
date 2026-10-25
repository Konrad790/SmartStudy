"use client";

import { BoardActions } from "@/components/board-list/board-actions";
import { useBoardsQuery, useCreateBoardMutation } from "@/hooks/useBoardsQuery";
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Sparkles, Plus, Search, Calendar, ArrowRight, LayoutGrid, Loader2 } from "lucide-react";

export function BoardsList() {
  const [title, setTitle] = useState("");
  const [filterQuery, setFilterQuery] = useState("");
  const router = useRouter();
  const boardsQuery = useBoardsQuery();
  const createBoard = useCreateBoardMutation();

  const onCreateNew = () => {
    const nextTitle = title.trim() || "Untitled Board";
    createBoard.mutate(nextTitle, {
      onSuccess: (board) => {
        setTitle("");
        router.push(`/boards/${board.id}`);
      },
    });
  };

  const filteredBoards = boardsQuery.data?.items.filter((b) =>
    b.title.toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Top Navbar */}
      <nav className="flex items-center justify-between rounded-2xl border border-slate-200/80 bg-white/80 px-6 py-4 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 text-white shadow-md shadow-indigo-500/20">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight text-slate-900">SmartStudy</span>
            <span className="ml-2 rounded-md bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700">
              Workspace
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <UserButton afterSignOutUrl="/sign-in" />
        </div>
      </nav>

      {/* Main Header / Actions */}
      <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Boards</h1>
          <p className="mt-1 text-sm text-slate-500">
            Create and organize study whiteboards with real-time AI assistance.
          </p>
        </div>

        {/* Quick Create Board Bar */}
        <div className="flex items-center gap-2">
          <div className="relative min-w-[240px]">
            <input
              className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-3.5 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 shadow-sm transition-all"
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onCreateNew();
              }}
              placeholder="New board title…"
              value={title}
            />
          </div>
          <button
            className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-indigo-500/20 hover:from-indigo-500 hover:to-violet-500 active:scale-[0.98] transition-all disabled:opacity-60"
            disabled={createBoard.isPending}
            onClick={onCreateNew}
            type="button"
          >
            {createBoard.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            <span>Create</span>
          </button>
        </div>
      </div>

      {/* Search & Stats Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between rounded-xl border border-slate-200/60 bg-white/60 p-2 backdrop-blur-sm">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            className="w-full rounded-lg border-0 bg-transparent py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Search boards…"
            value={filterQuery}
          />
        </div>
        <div className="flex items-center gap-2 px-3 text-xs text-slate-500 font-medium">
          <LayoutGrid className="h-3.5 w-3.5 text-slate-400" />
          <span>{filteredBoards?.length ?? 0} board{(filteredBoards?.length ?? 0) === 1 ? "" : "s"}</span>
        </div>
      </div>

      {/* Query Errors */}
      {boardsQuery.isError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-800">
          <p className="font-semibold">Unable to load boards</p>
          <p className="mt-1 text-xs text-rose-700">
            {boardsQuery.error instanceof Error ? boardsQuery.error.message : "Unknown error"}.
            {boardsQuery.error instanceof Error && boardsQuery.error.message === "Unauthorized" ? (
              <> Please <Link className="font-bold underline" href="/sign-in">sign in</Link>.</>
            ) : (
              <> Make sure backend is running (`npm run dev:api`).</>
            )}
          </p>
        </div>
      ) : null}

      {/* Loading Skeleton */}
      {boardsQuery.isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 rounded-2xl border border-slate-200 bg-white p-5 animate-pulse">
              <div className="h-6 w-3/4 rounded bg-slate-100" />
              <div className="mt-4 h-4 w-1/2 rounded bg-slate-100" />
              <div className="mt-12 h-6 w-1/3 rounded bg-slate-100" />
            </div>
          ))}
        </div>
      ) : null}

      {/* Boards Grid */}
      {filteredBoards && filteredBoards.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredBoards.map((board) => (
            <div
              key={board.id}
              className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm hover:border-indigo-300 hover:shadow-md hover:shadow-indigo-500/5 transition-all"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <Link
                    href={`/boards/${board.id}`}
                    className="font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1"
                  >
                    {board.title}
                  </Link>
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-all">
                    <ArrowRight className="h-3.5 w-3.5" />
                  </span>
                </div>

                <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>Recently active</span>
                </div>
              </div>

              <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-3">
                <Link
                  href={`/boards/${board.id}`}
                  className="text-xs font-medium text-indigo-600 hover:text-indigo-800 transition-colors"
                >
                  Open board &rarr;
                </Link>
                <BoardActions boardId={board.id} isDeleted={board.isDeleted} purgeAt={board.purgeAt} />
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Empty State */}
      {!boardsQuery.isLoading && (!filteredBoards || filteredBoards.length === 0) ? (
        <div className="flex flex-col items-center justify-center rounded-3xl border-2 border-dashed border-slate-200 bg-white/60 p-12 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 mb-4 shadow-inner">
            <Sparkles className="h-7 w-7" />
          </div>
          <h3 className="text-base font-semibold text-slate-800">No boards yet</h3>
          <p className="mt-1 text-xs text-slate-500 max-w-sm">
            Start your first session by creating a board above. Your sketches, math formulas, and notes will be autosaved automatically.
          </p>
        </div>
      ) : null}
    </div>
  );
}
