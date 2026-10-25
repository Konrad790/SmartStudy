import Link from "next/link";
import { Sparkles, ArrowRight, Eye, PenTool, Sigma, RefreshCw } from "lucide-react";

export default function HomePage() {
  return (
    <main className="relative min-h-screen overflow-x-hidden bg-[#f8fafc] text-slate-900">
      {/* Background ambient blurs */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 h-[500px] w-[800px] rounded-full bg-gradient-to-tr from-indigo-200/50 to-violet-200/40 blur-3xl" />
        <div className="absolute top-1/2 -right-40 h-[400px] w-[400px] rounded-full bg-indigo-100/40 blur-3xl" />
      </div>

      {/* Navigation */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-500/25">
            <Sparkles className="h-5 w-5" />
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900">SmartStudy</span>
        </div>

        <div className="flex items-center gap-3">
          <Link
            className="rounded-xl px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
            href="/sign-in"
          >
            Sign In
          </Link>
          <Link
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-sm shadow-indigo-500/25 hover:bg-indigo-700 active:scale-[0.98] transition-all"
            href="/boards"
          >
            <span>Open Boards</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="mx-auto max-w-4xl px-6 pt-16 pb-20 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200/80 bg-indigo-50/80 px-3.5 py-1 text-xs font-medium text-indigo-700 shadow-sm backdrop-blur-sm mb-6">
          <Sparkles className="h-3.5 w-3.5 text-indigo-600" />
          <span>Interactive Canvas Powered by Multimodal AI</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-slate-900 leading-[1.15]">
          The Infinite Whiteboard with an{" "}
          <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 bg-clip-text text-transparent">
            AI Tutor
          </span>{" "}
          by Your Side.
        </h1>

        <p className="mx-auto mt-6 max-w-2xl text-base sm:text-lg text-slate-600 leading-relaxed">
          Draw equations, sketch geometry, and brainstorm freely. SmartStudy reads your handwriting,
          solves tricky steps, and proposes real-time drawings straight onto your canvas.
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 hover:from-indigo-500 hover:to-violet-500 active:scale-[0.98] transition-all"
            href="/boards"
          >
            <span>Launch Workspace</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            className="inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white/90 px-6 py-3.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 active:scale-[0.98] transition-all"
            href="/sign-in"
          >
            Sign In with Clerk
          </Link>
        </div>
      </section>

      {/* Interactive Mock Preview Card */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="relative overflow-hidden rounded-3xl border border-slate-200/80 bg-white p-6 shadow-2xl shadow-indigo-500/10 backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-6">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-rose-400" />
              <div className="h-3 w-3 rounded-full bg-amber-400" />
              <div className="h-3 w-3 rounded-full bg-emerald-400" />
              <span className="ml-2 font-mono text-xs text-slate-400">whiteboard_session.canvas</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-600 font-medium">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              AI Vision Synced
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Canvas mockup area */}
            <div className="md:col-span-2 relative min-h-[260px] rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 p-6 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="inline-block rounded-xl bg-white p-3 shadow-sm border border-slate-200/60 font-mono text-sm text-indigo-700">
                  $\int x \cdot e^x dx = e^x(x - 1) + C$
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-16 w-32 rounded-xl border border-dashed border-indigo-400 bg-indigo-50/50 flex items-center justify-center text-xs text-indigo-600 font-medium">
                    [Diagram Proposal]
                  </div>
                </div>
              </div>
              <p className="text-xs text-slate-400">Full Excalidraw infinite vector canvas with pen, shapes & math.</p>
            </div>

            {/* AI Assistant preview */}
            <div className="flex flex-col justify-between rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-indigo-600 text-white">
                    <Sparkles className="h-3.5 w-3.5" />
                  </div>
                  <span className="text-xs font-bold text-slate-800">AI Tutor Response</span>
                </div>
                <div className="rounded-xl bg-slate-50 p-3 text-xs text-slate-600 leading-relaxed border border-slate-100">
                  Using integration by parts, we let $u = x$ and $dv = e^x dx$. Then $du = dx$ and $v = e^x$.
                </div>
              </div>
              <div className="mt-4 rounded-lg bg-indigo-50/70 p-2 text-[11px] text-indigo-700 font-medium border border-indigo-100">
                AI can draw coordinate axes or graphs directly onto your canvas!
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Pillars */}
      <section className="mx-auto max-w-5xl px-6 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 mb-3">
              <Eye className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">Multimodal Vision</h3>
            <p className="mt-1 text-xs text-slate-500 leading-relaxed">
              Detects updates on your board intelligently, focusing right on what changed.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-50 text-violet-600 mb-3">
              <PenTool className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">Drawing Suggestions</h3>
            <p className="mt-1 text-xs text-slate-500 leading-relaxed">
              The AI generates geometric shapes and graphs directly onto your whiteboard.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 mb-3">
              <Sigma className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">LaTeX & Math</h3>
            <p className="mt-1 text-xs text-slate-500 leading-relaxed">
              Crystal-clear typography for formulas, equations, proofs, and calculus.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-200/70 bg-white p-5 shadow-sm">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 mb-3">
              <RefreshCw className="h-5 w-5" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">Continuous Autosave</h3>
            <p className="mt-1 text-xs text-slate-500 leading-relaxed">
              Never lose your thoughts. Conflict-aware autosaving keeps your work safe.
            </p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200/60 py-8 text-center text-xs text-slate-400">
        <p>&copy; {new Date().getFullYear()} SmartStudy. Built for interactive, AI-guided learning.</p>
      </footer>
    </main>
  );
}
