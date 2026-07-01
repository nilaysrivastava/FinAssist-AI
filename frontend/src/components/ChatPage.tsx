import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  Database,
  FileText,
  Loader2,
  LockKeyhole,
  LogOut,
  Mail,
  Menu,
  MessageSquare,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  UserRound,
  Wrench,
  X,
} from "lucide-react";
import { clearToken, sendChat, sendEmailOffer } from "../api";
import type { ChatMessage, User } from "../types";
import Markdown from "./Markdown";

const SESSION_MESSAGES_KEY = "finassist_assist_current_session_messages";

const SHOW_TOOL_TRACE = import.meta.env.VITE_SHOW_TOOL_TRACE === "true";

const CUSTOMER_PROMPTS = [
  "What is my next EMI due date?",
  "Show my recent payment status.",
  "My payment is debited but not reflected. What should I do?",
  "How can I download my NOC?",
];

const EMPLOYEE_PROMPTS = [
  "Search customer Aarav and summarize his loan status.",
  "Find Priya customer record and recent payments.",
  "What is the escalation process for failed payment reconciliation?",
  "Draft a safe response for NOC not visible after loan closure.",
];

function getInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function getWelcomeMessage(user: User): ChatMessage {
  return {
    role: "assistant",
    content: `Hi ${user.name.split(" ")[0]}, I am FinAssist AI.\n\nI can help with EMI details, payment status, NOC guidance, support tickets, policy answers, customer records, employee workflows, citations, and safe human-approval routing.`,
  };
}

function loadSessionMessages(storageKey: string, user: User): ChatMessage[] {
  if (typeof window === "undefined") {
    return [getWelcomeMessage(user)];
  }

  const saved = window.sessionStorage.getItem(storageKey);

  if (!saved) {
    return [getWelcomeMessage(user)];
  }

  try {
    const parsed = JSON.parse(saved);

    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed as ChatMessage[];
    }
  } catch {
    window.sessionStorage.removeItem(storageKey);
  }

  return [getWelcomeMessage(user)];
}

export default function ChatPage({
  user,
  onLogout,
}: {
  user: User;
  onLogout: () => void;
}) {
  const sessionMessagesKey = `${SESSION_MESSAGES_KEY}_${user.id}`;

  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadSessionMessages(sessionMessagesKey, user)
  );

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sendingOfferId, setSendingOfferId] = useState<string | null>(null);
  const [sentOffers, setSentOffers] = useState<Record<string, string>>({});

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const prompts =
    user.role === "employee" ? EMPLOYEE_PROMPTS : CUSTOMER_PROMPTS;

  const subtitle = useMemo(() => {
    return user.role === "employee"
      ? "Employee workspace"
      : `Customer ID: ${user.customer_id}`;
  }, [user]);

  const canShowToolTrace = user.role === "employee" || SHOW_TOOL_TRACE;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: messages.length > 1 ? "smooth" : "auto",
      block: "end",
    });
  }, [messages.length, loading]);

  useEffect(() => {
    sessionStorage.setItem(sessionMessagesKey, JSON.stringify(messages));
  }, [messages, sessionMessagesKey]);

  function logout() {
    sessionStorage.removeItem(sessionMessagesKey);
    sessionStorage.removeItem(SESSION_MESSAGES_KEY);
    clearToken();
    onLogout();
  }

  function usePrompt(prompt: string) {
    setInput(prompt);
    setSidebarOpen(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  async function handleSendEmailOffer(offerId: string) {
    if (sendingOfferId) return;

    setSendingOfferId(offerId);

    try {
      const res = await sendEmailOffer(offerId);

      setSentOffers((prev) => ({
        ...prev,
        [offerId]: res.message || "Email sent successfully.",
      }));
    } catch (err) {
      setSentOffers((prev) => ({
        ...prev,
        [offerId]: err instanceof Error ? err.message : "Unable to send email.",
      }));
    } finally {
      setSendingOfferId(null);
    }
  }

  async function submit(e?: FormEvent) {
    e?.preventDefault();

    const text = input.trim();

    if (!text || loading) return;

    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: "user", content: text },
    ];

    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChat(text, nextMessages.slice(0, -1));

      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: res.answer,
          sources: res.sources,
          tool_trace: res.tool_trace,
          blocked: res.blocked,
          needs_human_approval: res.needs_human_approval,
          email_offer: res.email_offer,
        },
      ]);
    } catch (err) {
      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          blocked: true,
          content:
            err instanceof Error
              ? err.message
              : "Request failed. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const SidebarContent = (
    <aside className="flex h-full min-h-0 flex-col rounded-r-[2rem] bg-slate-950 p-4 text-white shadow-2xl">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-white text-slate-950 shadow-lg">
            <Bot size={22} />
          </div>

          <div className="min-w-0">
            <h1 className="truncate text-base font-black leading-tight">
              FinAssist AI
            </h1>
            <p className="truncate text-xs text-slate-400">Agentic RAG demo</p>
          </div>
        </div>

        <button
          type="button"
          className="rounded-xl p-2 text-slate-300 transition hover:bg-white/10"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close sidebar"
        >
          <X size={20} />
        </button>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/[0.07] p-4 shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-blue-500 text-sm font-black text-white">
            {getInitials(user.name)}
          </div>

          <div className="min-w-0">
            <p className="truncate text-sm font-black">{user.name}</p>
            <p className="truncate text-xs text-slate-300">{subtitle}</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-emerald-400/15 px-3 py-1 text-[11px] font-black uppercase tracking-wide text-emerald-200">
            {user.role}
          </span>
          <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-bold text-slate-300">
            Secure session
          </span>
        </div>
      </div>

      {/* <div className="mt-5 grid gap-2 text-sm">
        <div className="flex items-center gap-3 rounded-2xl bg-white/[0.06] p-3 text-slate-200">
          <FileText size={18} className="shrink-0 text-cyan-300" />
          <span className="min-w-0 truncate">Read-only policy KB</span>
        </div>

        <div className="flex items-center gap-3 rounded-2xl bg-white/[0.06] p-3 text-slate-200">
          <Search size={18} className="shrink-0 text-violet-300" />
          <span className="min-w-0 truncate">Hybrid search + reranking</span>
        </div>

        <div className="flex items-center gap-3 rounded-2xl bg-white/[0.06] p-3 text-slate-200">
          <Wrench size={18} className="shrink-0 text-amber-300" />
          <span className="min-w-0 truncate">Tool calling workflows</span>
        </div>

        <div className="flex items-center gap-3 rounded-2xl bg-white/[0.06] p-3 text-slate-200">
          <ShieldCheck size={18} className="shrink-0 text-emerald-300" />
          <span className="min-w-0 truncate">Guardrails + PII masking</span>
        </div>

        <div className="flex items-center gap-3 rounded-2xl bg-white/[0.06] p-3 text-slate-200">
          <Database size={18} className="shrink-0 text-blue-300" />
          <span className="min-w-0 truncate">JSON records + memory</span>
        </div>
      </div> */}

      {/* <div className="mt-5 grid gap-2 text-sm">
        <div className="flex items-center gap-3 rounded-2xl bg-white/[0.06] p-3 text-slate-200">
        Old chats will appear here in the next versions of this chatbot.
        </div>
      </div> */}

      <div className="scrollbar-thin mt-10 min-h-0 flex-1 overflow-y-auto pr-1">
        <p className="mb-3 text-md font-black uppercase tracking-widest text-slate-400">
          Try asking
        </p>

        <div className="grid gap-2">
          {prompts.map((prompt) => (
            <button
              type="button"
              key={prompt}
              onClick={() => usePrompt(prompt)}
              className="rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-3 text-left text-sm leading-5 text-slate-200 transition hover:border-white/20 hover:bg-white/10"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={logout}
        className="mt-5 flex items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-black text-slate-950 transition hover:bg-slate-100"
      >
        <LogOut size={18} />
        Logout
      </button>
    </aside>
  );

  return (
    <main className="h-[100dvh] w-full overflow-hidden bg-[radial-gradient(circle_at_top_left,#dbeafe,transparent_34%),linear-gradient(135deg,#f8fafc,#eef2ff)] p-0 sm:p-3 lg:p-4">
      <div className="mx-auto flex h-full min-h-0 w-full max-w-[1500px] overflow-hidden bg-white shadow-soft sm:rounded-[2rem]">
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-50 bg-slate-950/40 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          >
            <div
              className="h-full w-[86%] max-w-[340px] sm:max-w-[360px] lg:max-w-[390px]"
              onClick={(event) => event.stopPropagation()}
            >
              {SidebarContent}
            </div>
          </div>
        )}

        <section className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-col bg-white">
          <header className="flex shrink-0 items-center justify-between border-b border-slate-100 bg-white/95 px-4 py-4 backdrop-blur sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="rounded-xl border border-slate-200 p-2 text-slate-700 transition hover:bg-slate-50"
                aria-label="Open sidebar"
              >
                <Menu size={18} />
              </button>

              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-slate-950 text-white">
                <MessageSquare size={18} />
              </div>

              <div className="min-w-0">
                <h2 className="truncate text-base font-black text-slate-950 sm:text-lg">
                  Secure Chat
                </h2>
                {/* <p className="truncate text-xs font-semibold text-slate-500 sm:text-sm">
                  RAG + Vector Chunks + Hybrid Search + Reranking + Tools
                </p> */}
              </div>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-black text-slate-600 md:flex">
                <LockKeyhole size={14} />
                {user.role === "employee" ? "Internal mode" : "Customer mode"}
              </div>

              <button
                type="button"
                onClick={logout}
                className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-700 shadow-sm transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
              >
                <LogOut size={15} />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </header>

          <div className="scrollbar-thin min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-10">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-5">
              {messages.map((message, index) => {
                const isUser = message.role === "user";
                const sentMessage =
                  message.email_offer &&
                  sentOffers[message.email_offer.offer_id];

                return (
                  <div
                    key={index}
                    className={`flex w-full gap-3 ${
                      isUser ? "justify-end" : "justify-start"
                    }`}
                  >
                    {!isUser && (
                      <div className="mt-1 hidden h-9 w-9 shrink-0 place-items-center rounded-2xl bg-slate-950 text-white shadow-sm sm:grid">
                        <Bot size={18} />
                      </div>
                    )}

                    <div
                      className={
                        isUser
                          ? "max-w-[86%] rounded-[1.4rem] rounded-br-md bg-slate-950 px-5 py-4 text-sm leading-7 text-white shadow-sm sm:max-w-[70%]"
                          : message.blocked
                            ? "max-w-[min(820px,100%)] rounded-[1.4rem] rounded-tl-md border border-red-100 bg-red-50 px-5 py-4 text-sm leading-7 text-red-900 shadow-sm"
                            : message.needs_human_approval
                              ? "max-w-[min(820px,100%)] rounded-[1.4rem] rounded-tl-md border border-amber-100 bg-amber-50 px-5 py-4 text-sm leading-7 text-amber-950 shadow-sm"
                              : "max-w-[min(820px,100%)] rounded-[1.4rem] rounded-tl-md border border-slate-100 bg-slate-50 px-5 py-4 text-sm leading-7 text-slate-800 shadow-sm"
                      }
                    >
                      {!isUser && (
                        <div className="mb-3 flex items-center gap-2 text-xs font-black uppercase tracking-wide text-slate-500">
                          {message.needs_human_approval ? (
                            <AlertTriangle size={14} />
                          ) : (
                            <Sparkles size={14} />
                          )}
                          FinAssist AI
                        </div>
                      )}

                      <Markdown text={message.content} />

                      {message.email_offer && !isUser && (
                        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-200 pt-3">
                          {sentMessage ? (
                            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
                              <CheckCircle2 size={14} />
                              {sentMessage}
                            </span>
                          ) : (
                            <>
                              <span className="text-xs font-semibold text-slate-500">
                                Want this on email?
                              </span>

                              <button
                                type="button"
                                onClick={() =>
                                  handleSendEmailOffer(
                                    message.email_offer!.offer_id
                                  )
                                }
                                disabled={
                                  sendingOfferId ===
                                  message.email_offer.offer_id
                                }
                                className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-black text-blue-700 shadow-sm transition hover:border-blue-300 hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {sendingOfferId ===
                                message.email_offer.offer_id ? (
                                  <>
                                    <Loader2
                                      size={13}
                                      className="animate-spin"
                                    />
                                    Sending
                                  </>
                                ) : (
                                  <>
                                    <Mail size={13} />
                                    Send email
                                  </>
                                )}
                              </button>
                            </>
                          )}
                        </div>
                      )}

                      {!!message.sources?.length && !isUser && (
                        <details className="mt-3 rounded-xl border border-slate-200 bg-white/70 text-xs text-slate-500">
                          <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 font-black text-slate-600">
                            <span>Sources used ({message.sources.length})</span>
                            <ChevronDown size={14} className="shrink-0" />
                          </summary>

                          <div className="scrollbar-thin max-h-28 space-y-1 overflow-y-auto border-t border-slate-100 px-3 py-2">
                            {message.sources.map((source) => (
                              <div
                                key={`${source.id}-${source.chunk_id}`}
                                className="rounded-lg bg-slate-50 px-2 py-1 text-[11px] font-semibold leading-5 text-slate-500"
                                title={source.citation || undefined}
                              >
                                <span className="font-black text-slate-600">
                                  {source.title}
                                </span>
                                <span className="mx-1">·</span>
                                <span>{source.section || source.category}</span>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}

                      {canShowToolTrace &&
                        !!message.tool_trace?.length &&
                        !isUser && (
                          <details className="mt-2 rounded-xl border border-slate-200 bg-white/70 text-xs text-slate-500">
                            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 font-black text-slate-600">
                              <span>
                                Tools used ({message.tool_trace.length})
                              </span>
                              <ChevronDown size={14} className="shrink-0" />
                            </summary>

                            <div className="scrollbar-thin max-h-24 space-y-1 overflow-y-auto border-t border-slate-100 px-3 py-2">
                              {message.tool_trace.map((trace, traceIndex) => (
                                <div
                                  key={traceIndex}
                                  className="rounded-lg bg-slate-50 px-2 py-1 text-[11px] leading-5"
                                >
                                  <span className="font-black text-slate-600">
                                    {trace.tool}
                                  </span>{" "}
                                  →{" "}
                                  {trace.human_approval_required
                                    ? "human approval"
                                    : trace.allowed
                                      ? "allowed"
                                      : `blocked: ${trace.reason}`}
                                </div>
                              ))}
                            </div>
                          </details>
                        )}
                    </div>

                    {isUser && (
                      <div className="mt-1 hidden h-9 w-9 shrink-0 place-items-center rounded-2xl bg-blue-600 text-xs font-black text-white shadow-sm sm:grid">
                        <UserRound size={16} />
                      </div>
                    )}
                  </div>
                );
              })}

              {loading && (
                <div className="flex w-full justify-start gap-3">
                  <div className="mt-1 hidden h-9 w-9 shrink-0 place-items-center rounded-2xl bg-slate-950 text-white shadow-sm sm:grid">
                    <Bot size={18} />
                  </div>

                  <div className="flex items-center gap-3 rounded-[1.4rem] rounded-tl-md border border-slate-100 bg-slate-50 px-5 py-4 text-sm font-bold text-slate-500 shadow-sm">
                    <Loader2 size={17} className="animate-spin" />
                    Thinking...
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>
          </div>

          <form
            onSubmit={submit}
            className="shrink-0 border-t border-slate-100 bg-white/95 px-4 py-4 backdrop-blur sm:px-6 lg:px-10"
          >
            <div className="scrollbar-thin mx-auto mb-3 flex w-full max-w-4xl gap-2 overflow-x-auto pb-1">
              {prompts.map((prompt) => (
                <button
                  type="button"
                  key={prompt}
                  onClick={() => usePrompt(prompt)}
                  className="shrink-0 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600 shadow-sm transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                >
                  {prompt}
                </button>
              ))}
            </div>

            <div className="mx-auto flex w-full max-w-4xl items-end gap-3 rounded-[1.6rem] border border-slate-200 bg-slate-50 p-2 shadow-sm transition focus-within:border-blue-400 focus-within:bg-white focus-within:shadow-md">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                rows={1}
                placeholder="Ask about EMI, NOC, payment status, policy, customer record, or support workflow..."
                className="max-h-36 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm leading-6 text-slate-900 outline-none placeholder:text-slate-400"
              />

              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-slate-950 text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {loading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}
