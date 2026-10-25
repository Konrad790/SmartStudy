"use client";

import { AlertTriangle } from "lucide-react";

export function StaleStateBanner({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <div className="pointer-events-auto flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50/95 px-3 py-2 text-xs font-medium text-amber-900 shadow-md backdrop-blur-md">
      <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
      <span>Your view is outdated. Refresh the page to sync the latest board changes.</span>
    </div>
  );
}
