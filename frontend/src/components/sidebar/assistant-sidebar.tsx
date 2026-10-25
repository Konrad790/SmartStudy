"use client";

import { AssistantMessageContent } from "@/components/sidebar/assistant-message-content";
import {
  AssistantChatPayload,
  AssistantChatResponse,
  TodrawPlan,
  useAssistantChat,
  useConversations,
  ConversationItem,
} from "@/hooks/useAssistantChat";
import type { VisionSyncStatus, PreparedBoardContext } from "@/hooks/useBoardVisionSync";
import type { BoardImagePayload } from "@/lib/excalidraw/export-board-image";
import { FormEvent, memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Sparkles,
  Send,
  Loader2,
  PenTool,
  ChevronDown,
  CheckCircle2,
  Clock,
  AlertCircle,
  Plus,
  History,
  Trash2,
  ArrowLeft,
  MessageSquare,
} from "lucide-react";

type SessionMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  boardContextJson?: Record<string, unknown> | null;
  todraw?: TodrawPlan | null;
  isStreaming?: boolean;
};

function nextMessageId() {
  return crypto.randomUUID();
}

function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHours = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

const ConversationMessageItem = memo(function ConversationMessageItem({
  item,
}: {
  item: SessionMessage;
}) {
  if (item.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-gradient-to-r from-indigo-600 to-violet-600 px-3.5 py-2.5 text-xs text-white shadow-sm shadow-indigo-500/10">
          {item.content}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-indigo-100 text-indigo-700">
          <Sparkles className="h-3 w-3" />
        </div>
        <div className="flex-1 overflow-hidden">
          <AssistantMessageContent content={item.content} isStreaming={item.isStreaming} />
        </div>
      </div>

      {item.todraw ? (
        <div className="ml-7 flex items-center gap-1.5 rounded-xl border border-indigo-100 bg-indigo-50/70 px-2.5 py-1.5 text-[11px] text-indigo-900">
          <PenTool className="h-3.5 w-3.5 text-indigo-600 shrink-0" />
          <span>
            Drawing plan ready
            {typeof item.todraw.summary === "string" && item.todraw.summary
              ? `: ${item.todraw.summary}`
              : ""}
          </span>
        </div>
      ) : null}

      {item.boardContextJson ? (
        <details className="group ml-7 rounded-xl border border-slate-200/70 bg-slate-50/80 p-2 text-[11px] text-slate-600">
          <summary className="flex cursor-pointer items-center justify-between font-medium select-none">
            <span>Board Context JSON</span>
            <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180 text-slate-400" />
          </summary>
          <pre className="mt-2 max-h-36 overflow-auto rounded-lg bg-slate-900 p-2 text-[10px] text-slate-200 font-mono whitespace-pre-wrap">
            {JSON.stringify(item.boardContextJson, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  );
});

const AssistantChatInput = memo(function AssistantChatInput({
  onSend,
  disabled,
  sendError,
}: {
  onSend: (message: string) => void;
  disabled: boolean;
  sendError: string | null;
}) {
  const [message, setMessage] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || disabled) return;
    setMessage("");
    onSend(trimmed);
  };

  return (
    <form className="flex flex-col gap-2 pt-2 border-t border-slate-100" onSubmit={handleSubmit}>
      <div className="relative flex items-center">
        <input
          aria-label="Assistant chat input"
          className="w-full rounded-xl border border-slate-200 bg-slate-50/80 py-2.5 pl-3.5 pr-10 text-xs text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all"
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask a question (LaTeX supported, e.g. $x^2$)..."
          value={message}
          disabled={disabled}
        />
        <button
          className="absolute right-1.5 flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm hover:bg-indigo-700 disabled:opacity-40 disabled:hover:bg-indigo-600 transition-all"
          disabled={disabled || !message.trim()}
          type="submit"
          aria-label="Send message"
        >
          {disabled ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
        </button>
      </div>
      {sendError ? (
        <div className="flex items-center gap-1.5 text-[11px] text-rose-600 px-1">
          <AlertCircle className="h-3 w-3 shrink-0" />
          <span>{sendError}</span>
        </div>
      ) : null}
    </form>
  );
});

export function AssistantSidebar({
  boardId,
  captureBoardImage,
  prepareBoardContext,
  syncStatus,
  onTodraw,
  onClose,
  className,
}: {
  boardId: string;
  captureBoardImage?: () => Promise<BoardImagePayload | null>;
  prepareBoardContext?: () => Promise<PreparedBoardContext>;
  syncStatus?: VisionSyncStatus;
  onTodraw?: (
    todraw: TodrawPlan,
    meta?: {
      boardContextJson?: Record<string, unknown> | null;
      visibleViewport?: BoardImagePayload["visibleViewport"];
    }
  ) => Promise<void>;
  onClose?: () => void;
  className?: string;
}) {
  const [sendError, setSendError] = useState<string | null>(null);
  const [conversation, setConversation] = useState<SessionMessage[]>([]);
  const [drawStatus, setDrawStatus] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null);

  // Conversation history states
  const [showHistory, setShowHistory] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const hasInitializedConversationRef = useRef<boolean>(false);

  const endOfConversationRef = useRef<HTMLDivElement | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const tokensQueueRef = useRef<string[]>([]);
  const accumulatedContentRef = useRef<string>("");
  const activeMsgIdRef = useRef<string | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const streamCompletedRef = useRef<boolean>(false);
  const finalResponseRef = useRef<AssistantChatResponse | null>(null);
  const viewportForDrawRef = useRef<BoardImagePayload["visibleViewport"] | null>(null);

  const chat = useAssistantChat(boardId);
  const {
    conversations,
    isLoading: isConversationsLoading,
    deleteConversation,
    fetchMessages,
    refetch: refetchConversations,
  } = useConversations(boardId);

  // Active conversation object
  const activeConversation = useMemo(() => {
    if (!activeConversationId) return null;
    return conversations.find((c) => c.id === activeConversationId) ?? null;
  }, [activeConversationId, conversations]);

  // Load the selected conversation messages
  const selectConversation = useCallback(
    async (convId: string | null) => {
      // Abort any ongoing stream
      abortControllerRef.current?.abort();
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setIsStreaming(false);
      setStreamingStatus(null);
      setSendError(null);
      setDrawStatus(null);

      setActiveConversationId(convId);
      setShowHistory(false);

      if (!convId) {
        setConversation([]);
        return;
      }

      setIsLoadingMessages(true);
      try {
        const msgs = await fetchMessages(convId);
        setConversation(
          msgs.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
          }))
        );
      } catch (err) {
        setSendError(err instanceof Error ? err.message : "Failed to load conversation history.");
        setConversation([]);
      } finally {
        setIsLoadingMessages(false);
      }
    },
    [fetchMessages]
  );

  // Start a fresh conversation (Antigravity-like "+ New chat")
  const startNewConversation = useCallback(() => {
    void selectConversation(null);
  }, [selectConversation]);

  // Initialize: when conversations load for this board, select the most recent one if available
  useEffect(() => {
    if (hasInitializedConversationRef.current) return;
    if (!isConversationsLoading && conversations.length > 0) {
      hasInitializedConversationRef.current = true;
      void selectConversation(conversations[0].id);
    }
  }, [conversations, isConversationsLoading, selectConversation]);

  // Handle boardId change: reset initialized ref & active conversation
  useEffect(() => {
    hasInitializedConversationRef.current = false;
    abortControllerRef.current?.abort();
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    tokensQueueRef.current = [];
    accumulatedContentRef.current = "";
    activeMsgIdRef.current = null;
    streamCompletedRef.current = false;
    finalResponseRef.current = null;
    setIsStreaming(false);
    setStreamingStatus(null);
    setConversation([]);
    setSendError(null);
    setDrawStatus(null);
    setActiveConversationId(null);
    setShowHistory(false);
  }, [boardId]);

  const processQueueTick = useCallback(() => {
    const currentMsgId = activeMsgIdRef.current;
    if (!currentMsgId) return;

    const queue = tokensQueueRef.current;
    if (queue.length > 0) {
      const count = queue.length > 10 ? Math.ceil(queue.length / 4) : queue.length > 4 ? 2 : 1;
      const popped = queue.splice(0, count);
      accumulatedContentRef.current += popped.join("");
      const newContent = accumulatedContentRef.current;

      setConversation((current) =>
        current.map((msg) =>
          msg.id === currentMsgId ? { ...msg, content: newContent } : msg
        )
      );
    }

    if (streamCompletedRef.current && queue.length === 0) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      const finalResp = finalResponseRef.current;
      if (finalResp) {
        if (finalResp.conversationId && finalResp.conversationId !== activeConversationId) {
          setActiveConversationId(finalResp.conversationId);
          void refetchConversations();
        }

        setConversation((current) =>
          current.map((msg) =>
            msg.id === currentMsgId
              ? {
                  ...msg,
                  content: finalResp.message,
                  boardContextJson: finalResp.boardContextJson,
                  todraw: finalResp.todraw ?? null,
                  isStreaming: false,
                }
              : msg
          )
        );

        if (finalResp.todraw && onTodraw) {
          setDrawStatus("Preparing drawing suggestion…");
          const vp = viewportForDrawRef.current;
          void onTodraw(finalResp.todraw, {
            boardContextJson: finalResp.boardContextJson,
            visibleViewport: vp,
          })
            .then(() => {
              setDrawStatus("Drawing suggestion ready — Accept or Reject on the board.");
            })
            .catch((err) => {
              setDrawStatus(err instanceof Error ? err.message : "Drawing suggestion failed.");
            });
        }
      }
      setIsStreaming(false);
      setStreamingStatus(null);
      activeMsgIdRef.current = null;
    }
  }, [activeConversationId, onTodraw, refetchConversations]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    endOfConversationRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [conversation, isStreaming, drawStatus]);

  const sendChat = useCallback(
    async (userMessageText: string) => {
      const userMessage = userMessageText.trim();
      if (!userMessage || isStreaming) return;
      setSendError(null);
      setDrawStatus(null);

      abortControllerRef.current?.abort();
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      try {
        let chatPayload: AssistantChatPayload = {
          message: userMessage,
          conversationId: activeConversationId ?? undefined,
        };
        let viewportForDraw: BoardImagePayload["visibleViewport"] = null;

        if (prepareBoardContext) {
          const prepared = await prepareBoardContext();
          viewportForDraw = prepared.visibleViewport ?? null;
          if (prepared.boardImageBase64 && prepared.boardImageMimeType) {
            chatPayload = {
              message: userMessage,
              conversationId: activeConversationId ?? undefined,
              boardImageMimeType: prepared.boardImageMimeType,
              boardImageBase64: prepared.boardImageBase64,
              patchBbox: prepared.patchBbox,
              visibleViewport: prepared.visibleViewport,
            };
          } else if (prepared.visibleViewport) {
            chatPayload = {
              message: userMessage,
              conversationId: activeConversationId ?? undefined,
              visibleViewport: prepared.visibleViewport,
            };
          }
        } else if (captureBoardImage) {
          const boardImage = await captureBoardImage();
          if (boardImage) {
            viewportForDraw = boardImage.visibleViewport;
            chatPayload = {
              message: userMessage,
              conversationId: activeConversationId ?? undefined,
              ...boardImage,
            };
          }
        }

        viewportForDrawRef.current = viewportForDraw;

        const userMsgId = nextMessageId();
        const assistantMsgId = nextMessageId();

        tokensQueueRef.current = [];
        accumulatedContentRef.current = "";
        activeMsgIdRef.current = assistantMsgId;
        streamCompletedRef.current = false;
        finalResponseRef.current = null;

        setConversation((current) => [
          ...current,
          {
            id: userMsgId,
            role: "user",
            content: userMessage,
          },
          {
            id: assistantMsgId,
            role: "assistant",
            content: "",
            isStreaming: true,
          },
        ]);
        setIsStreaming(true);
        setStreamingStatus("Thinking…");

        timerRef.current = setInterval(processQueueTick, 28);

        await chat.streamChat(
          chatPayload,
          {
            onStatus: (status) => {
              setStreamingStatus(status.message);
            },
            onDelta: (deltaText) => {
              const tokens = deltaText.match(/\S+\s*|\s+/g) || [deltaText];
              tokensQueueRef.current.push(...tokens);
            },
            onDone: (finalResp) => {
              finalResponseRef.current = finalResp;
              streamCompletedRef.current = true;
              if (finalResp.conversationId && finalResp.conversationId !== activeConversationId) {
                setActiveConversationId(finalResp.conversationId);
                void refetchConversations();
              }
            },
            onError: (err) => {
              setSendError(err.message);
            },
          },
          abortController.signal
        );
      } catch (err) {
        if (abortController.signal.aborted) return;
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setIsStreaming(false);
        setStreamingStatus(null);
        const currentMsgId = activeMsgIdRef.current;
        if (currentMsgId) {
          if (!accumulatedContentRef.current.trim()) {
            setConversation((curr) => curr.filter((m) => m.id !== currentMsgId));
          } else {
            setConversation((curr) =>
              curr.map((m) => (m.id === currentMsgId ? { ...m, isStreaming: false } : m))
            );
          }
        }
        setSendError(err instanceof Error ? err.message : "Request failed.");
      }
    },
    [
      activeConversationId,
      captureBoardImage,
      chat,
      isStreaming,
      prepareBoardContext,
      processQueueTick,
      refetchConversations,
    ]
  );

  const handleDeleteConversation = useCallback(
    async (e: React.MouseEvent, convId: string) => {
      e.stopPropagation();
      try {
        await deleteConversation(convId);
        if (activeConversationId === convId) {
          setActiveConversationId(null);
          setConversation([]);
        }
      } catch (err) {
        setSendError(err instanceof Error ? err.message : "Failed to delete conversation.");
      }
    },
    [activeConversationId, deleteConversation]
  );

  return (
    <aside
      className={`flex w-full flex-col h-full bg-white/95 backdrop-blur-xl border border-slate-200/80 shadow-2xl rounded-2xl p-4 text-slate-900 ${className ?? ""}`}
    >
      {/* Top Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 text-white shadow-sm shadow-indigo-500/30">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <h3 className="text-sm font-semibold text-slate-900 leading-tight truncate" id="assistant-heading">
                {showHistory ? "Conversations" : activeConversation?.title || "New Chat"}
              </h3>
            </div>
            <p className="text-[11px] text-slate-400 truncate">
              {showHistory ? "Select or start a chat" : "Interactive Whiteboard Tutor"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {syncStatus && !showHistory && (
            <div className="flex items-center text-[11px]">
              {syncStatus === "syncing" && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 font-medium border border-amber-200/60 animate-pulse">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  Scanning…
                </span>
              )}
              {syncStatus === "synced" && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-medium border border-emerald-200/60">
                  <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                  Synced
                </span>
              )}
              {syncStatus === "cooldown" && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-50 text-slate-500 font-medium border border-slate-200/60" title="Changes queued for background sync">
                  <Clock className="h-3 w-3 text-slate-400" />
                  Queued
                </span>
              )}
            </div>
          )}

          {/* New Chat Button */}
          <button
            onClick={startNewConversation}
            type="button"
            className="flex items-center gap-1 rounded-lg border border-slate-200/70 bg-slate-50/80 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-600 transition-all active:scale-95"
            title="Start a new conversation"
            aria-label="Start a new conversation"
          >
            <Plus className="h-3.5 w-3.5 text-indigo-600" />
            <span className="hidden sm:inline">New</span>
          </button>

          {/* Toggle History Button */}
          <button
            onClick={() => setShowHistory((prev) => !prev)}
            type="button"
            className={`flex items-center gap-1 rounded-lg border px-2 py-1 text-xs font-medium transition-all active:scale-95 ${
              showHistory
                ? "border-indigo-200 bg-indigo-50 text-indigo-700"
                : "border-slate-200/70 bg-slate-50/80 text-slate-700 hover:bg-slate-100 hover:text-slate-900"
            }`}
            title={showHistory ? "Back to chat" : "Conversation history"}
            aria-label="Conversation history"
          >
            {showHistory ? (
              <>
                <ArrowLeft className="h-3.5 w-3.5 text-indigo-600" />
                <span className="hidden sm:inline">Chat</span>
              </>
            ) : (
              <>
                <History className="h-3.5 w-3.5 text-slate-500" />
                {conversations.length > 0 && (
                  <span className="ml-0.5 rounded-full bg-indigo-100 px-1.5 py-0.2 font-mono text-[10px] font-semibold text-indigo-700">
                    {conversations.length}
                  </span>
                )}
              </>
            )}
          </button>

          {/* Close Panel Button */}
          {onClose && (
            <button
              onClick={onClose}
              type="button"
              className="rounded-lg p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              aria-label="Close assistant panel"
            >
              <span className="text-base leading-none">&times;</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area: History List or Chat View */}
      {showHistory ? (
        <div className="flex min-h-0 flex-1 flex-col py-3">
          <div className="flex items-center justify-between pb-2 mb-2">
            <span className="text-xs font-medium text-slate-500">
              {conversations.length} {conversations.length === 1 ? "thread" : "threads"} on this board
            </span>
            <button
              onClick={startNewConversation}
              type="button"
              className="flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700"
            >
              <Plus className="h-3 w-3" />
              <span>Start new chat</span>
            </button>
          </div>

          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
            {isConversationsLoading ? (
              <div className="flex h-32 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
              </div>
            ) : conversations.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center p-6 text-center text-slate-400">
                <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
                  <MessageSquare className="h-5 w-5" />
                </div>
                <p className="text-xs font-medium text-slate-600">No conversations yet</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Send a message to your whiteboard tutor to start your first conversation.
                </p>
                <button
                  onClick={startNewConversation}
                  type="button"
                  className="mt-4 flex items-center gap-1.5 rounded-xl bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-indigo-700 transition-all"
                >
                  <Plus className="h-3.5 w-3.5" />
                  <span>New conversation</span>
                </button>
              </div>
            ) : (
              conversations.map((conv: ConversationItem) => {
                const isActive = conv.id === activeConversationId;
                return (
                  <div
                    key={conv.id}
                    onClick={() => void selectConversation(conv.id)}
                    className={`group relative flex cursor-pointer flex-col gap-1 rounded-xl border p-2.5 transition-all text-left ${
                      isActive
                        ? "border-indigo-400/80 bg-indigo-50/70 shadow-sm ring-1 ring-indigo-400/30"
                        : "border-slate-200/70 bg-white hover:border-slate-300 hover:bg-slate-50/70"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <MessageSquare
                          className={`h-3.5 w-3.5 shrink-0 ${
                            isActive ? "text-indigo-600" : "text-slate-400"
                          }`}
                        />
                        <span
                          className={`text-xs font-semibold truncate ${
                            isActive ? "text-indigo-900" : "text-slate-800"
                          }`}
                        >
                          {conv.title}
                        </span>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {isActive && (
                          <span className="rounded-md bg-indigo-100/90 px-1.5 py-0.5 text-[9px] font-semibold text-indigo-700">
                            Active
                          </span>
                        )}
                        <button
                          type="button"
                          onClick={(e) => void handleDeleteConversation(e, conv.id)}
                          className="opacity-0 group-hover:opacity-100 rounded-md p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition-all"
                          title="Delete conversation"
                          aria-label="Delete conversation"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>

                    {conv.lastMessagePreview ? (
                      <p className="text-[11px] text-slate-500 line-clamp-1 pl-5">
                        {conv.lastMessagePreview}
                      </p>
                    ) : null}

                    <div className="flex items-center justify-between pl-5 pt-1 text-[10px] text-slate-400">
                      <span>{formatRelativeTime(conv.updatedAt)}</span>
                      <span>
                        {conv.messageCount} {conv.messageCount === 1 ? "msg" : "msgs"}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      ) : (
        /* Conversation Thread View */
        <div className="flex min-h-0 flex-1 flex-col gap-3 py-3">
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
            {isLoadingMessages ? (
              <div className="flex h-full items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
              </div>
            ) : conversation.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center p-6 text-center text-slate-400">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-500 shadow-sm">
                  <Sparkles className="h-6 w-6" />
                </div>
                <p className="text-xs font-semibold text-slate-700">How can I help you learn?</p>
                <p className="mt-1 text-[11px] text-slate-400 max-w-[240px]">
                  Ask questions about anything drawn on your whiteboard, solve equations, or request diagrams.
                </p>

                {/* Helpful quick prompt suggestions */}
                <div className="mt-4 flex flex-col gap-1.5 w-full max-w-[260px]">
                  <button
                    type="button"
                    onClick={() => void sendChat("Explain what is on the board")}
                    className="text-left rounded-xl border border-slate-200/80 bg-slate-50/60 hover:bg-indigo-50/70 hover:border-indigo-200 p-2 text-[11px] text-slate-600 hover:text-indigo-700 transition-all"
                  >
                    💡 Explain what is currently on the board
                  </button>
                  <button
                    type="button"
                    onClick={() => void sendChat("Solve the equation step by step")}
                    className="text-left rounded-xl border border-slate-200/80 bg-slate-50/60 hover:bg-indigo-50/70 hover:border-indigo-200 p-2 text-[11px] text-slate-600 hover:text-indigo-700 transition-all"
                  >
                    ✏️ Solve the problem step-by-step
                  </button>
                  <button
                    type="button"
                    onClick={() => void sendChat("Draw a summary diagram of these concepts")}
                    className="text-left rounded-xl border border-slate-200/80 bg-slate-50/60 hover:bg-indigo-50/70 hover:border-indigo-200 p-2 text-[11px] text-slate-600 hover:text-indigo-700 transition-all"
                  >
                    🎨 Draw a diagram on the whiteboard
                  </button>
                </div>
              </div>
            ) : null}

            {conversation.map((item) => (
              <ConversationMessageItem key={item.id} item={item} />
            ))}

            {isStreaming && streamingStatus ? (
              <div className="flex items-center gap-2 text-xs text-indigo-600 pl-7 py-1">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-600" />
                <span>{streamingStatus}</span>
              </div>
            ) : null}

            {drawStatus ? (
              <div className="ml-7 flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 p-2 rounded-xl border border-amber-200/60">
                <Sparkles className="h-3.5 w-3.5 text-amber-600 shrink-0" />
                <span>{drawStatus}</span>
              </div>
            ) : null}

            <div ref={endOfConversationRef} />
          </div>

          {/* Isolated Input Bar */}
          <AssistantChatInput
            onSend={sendChat}
            disabled={isStreaming || isLoadingMessages}
            sendError={sendError}
          />
        </div>
      )}
    </aside>
  );
}
