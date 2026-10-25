import { BoardsList } from "@/components/board-list/boards-list";

export default function BoardsPage() {
  return (
    <main className="relative min-h-screen bg-[#f8fafc] text-slate-900 overflow-x-hidden">
      {/* Subtle ambient gradient mesh background */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-40 right-0 h-96 w-96 rounded-full bg-indigo-100/60 blur-3xl" />
        <div className="absolute top-1/3 -left-40 h-96 w-96 rounded-full bg-violet-100/50 blur-3xl" />
      </div>

      <div className="mx-auto w-full max-w-6xl px-4 py-8 md:px-8">
        <BoardsList />
      </div>
    </main>
  );
}
