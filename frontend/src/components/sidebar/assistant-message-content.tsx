"use client";

import { memo, useMemo, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import { formatAssistantText } from "@/lib/utils/format-assistant-text";
import "katex/dist/katex.min.css";

const REMARK_PLUGINS = [remarkMath];
const REHYPE_PLUGINS = [rehypeKatex];

const MARKDOWN_COMPONENTS = {
  p: ({ children }: { children?: ReactNode }) => (
    <p className="leading-relaxed whitespace-pre-wrap mb-2 last:mb-0">
      {children}
    </p>
  ),
  ol: ({ children }: { children?: ReactNode }) => (
    <ol className="list-decimal list-outside pl-4 space-y-1 mb-2">
      {children}
    </ol>
  ),
  ul: ({ children }: { children?: ReactNode }) => (
    <ul className="list-disc list-outside pl-4 space-y-1 mb-2">
      {children}
    </ul>
  ),
  li: ({ children }: { children?: ReactNode }) => (
    <li className="leading-relaxed">{children}</li>
  ),
  strong: ({ children }: { children?: ReactNode }) => (
    <strong className="font-semibold text-slate-900">{children}</strong>
  ),
  code: ({ children }: { children?: ReactNode }) => (
    <code className="bg-slate-200/60 rounded px-1 py-0.5 font-mono text-[11px] text-slate-800">
      {children}
    </code>
  ),
  blockquote: ({ children }: { children?: ReactNode }) => (
    <blockquote className="border-l-2 border-indigo-400 pl-2.5 my-2 italic text-slate-600">
      {children}
    </blockquote>
  ),
};

export const AssistantMessageContent = memo(function AssistantMessageContent({
  content,
  isStreaming = false,
}: {
  content: string;
  isStreaming?: boolean;
}) {
  const formattedContent = useMemo(() => formatAssistantText(content), [content]);

  return (
    <div className="assistant-message rounded-2xl bg-slate-50 border border-slate-200/60 p-3.5 text-xs text-slate-700 leading-relaxed shadow-sm min-h-[38px] flex flex-col justify-center">
      {formattedContent ? (
        <div className="space-y-2">
          <ReactMarkdown
            remarkPlugins={REMARK_PLUGINS}
            rehypePlugins={REHYPE_PLUGINS}
            components={MARKDOWN_COMPONENTS}
          >
            {formattedContent}
          </ReactMarkdown>
          {isStreaming && (
            <span
              className="inline-block w-1.5 h-3.5 bg-indigo-500 rounded-sm ml-1 animate-pulse align-middle"
              aria-hidden="true"
            />
          )}
        </div>
      ) : isStreaming ? (
        <div className="flex items-center gap-1.5 text-slate-400 py-0.5">
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: "0ms" }} />
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: "150ms" }} />
          <span className="h-1.5 w-1.5 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      ) : null}
    </div>
  );
});
