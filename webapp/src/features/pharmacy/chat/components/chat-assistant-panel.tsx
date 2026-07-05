"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { User, Bot, Sparkles, Clock } from "lucide-react";
import type { ChatMessage, ChatRole, JsonObject } from "@/features/pharmacy/chat/types/chat-assistant";
import { CHAT_INITIAL_ASSISTANT_MESSAGE } from "@/features/pharmacy/chat/constants/chat-assistant";
import { routes } from "@/lib/constants/routes";
import { getAuthHeader } from "@/lib/api/client";

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function readText(value: unknown, fallback = ""): string {
  if (typeof value === "string") return value.trim() || fallback;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}
function createMessage(role: ChatRole, content: string, extras?: Partial<ChatMessage>): ChatMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    timestamp: Date.now(),
    ...extras,
  };
}

function stripToolJsonArtifacts(content: string): string {
  let cleaned = content;
  cleaned = cleaned.replace(/Jawaban\s+JSON\s+Tool[\s\S]*?(?=\n\s*\n|$)/gi, "");
  cleaned = cleaned.replace(
    /{[\s\n]*"tool"\s*:\s*"[^"]+"[\s\S]*?"arguments"[\s\S]*?}/g,
    ""
  );
  cleaned = cleaned.replace(
    /{[\s\n]*'tool'\s*:\s*'[^']+'[\s\S]*?'arguments'[\s\S]*?}/g,
    ""
  );
  cleaned = cleaned.replace(/```json[\s\S]*?```/gi, (block) => {
    if (/["']tool["']\s*:/.test(block)) return "";
    return block;
  });
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");
  return cleaned;
}

function normalizeAssistantContent(content: string): string {
  let cleaned = content;
  cleaned = cleaned.replace(/<unused\d+>thought[\s\S]*?(?:<unused\d+>|$)/g, "");
  cleaned = cleaned.replace(/<unused\d+>/g, "");
  cleaned = stripToolJsonArtifacts(cleaned);
  return cleaned.trim();
}

// Render teks pesan dengan markdown proper — bold, italic, list, dll
function MessageContent({ content, isUser }: { content: string; isUser: boolean }) {
  if (isUser) {
    return <p className="leading-relaxed whitespace-pre-wrap text-slate-800">{content}</p>;
  }

  const actualContent = normalizeAssistantContent(content);

  // Pesan AI: render markdown dengan komponen custom (tanpa @tailwindcss/typography)
  return (
    <div className="space-y-4">
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed text-slate-800">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
          em: ({ children }) => <em className="italic text-slate-800">{children}</em>,
          ul: ({ children }) => <ul className="mb-3 ml-5 list-disc space-y-1.5 text-slate-800">{children}</ul>,
          ol: ({ children }) => <ol className="mb-3 ml-5 list-decimal space-y-1.5 text-slate-800">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed pl-1">{children}</li>,
          h1: ({ children }) => <h1 className="mb-2 mt-4 text-xl font-bold text-slate-900">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 mt-4 text-lg font-bold text-slate-900">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 mt-3 text-base font-semibold text-slate-900">{children}</h3>,
          code: ({ children }) => <code className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[13px] font-mono text-emerald-700">{children}</code>,
          blockquote: ({ children }) => <blockquote className="border-l-4 border-emerald-500 bg-emerald-50/50 py-1 pl-4 my-3 italic text-slate-700 rounded-r-lg">{children}</blockquote>,
        }}
      >
        {actualContent || "Menyelesaikan..."}
      </ReactMarkdown>
    </div>
  );
}

const CHAT_SESSION_KEY = "pharmacy_chat_history";

function saveChatHistory(messages: ChatMessage[]) {
  try {
    sessionStorage.setItem(CHAT_SESSION_KEY, JSON.stringify(messages));
  } catch {}
}

// Hanya dipanggil di client setelah hydration
function formatTime(ts: number): string {
  return new Intl.DateTimeFormat("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(ts));
}

function formatDurationMs(ms: number): string {
  if (!Number.isFinite(ms)) return "-";
  const safeMs = Math.max(0, ms);
  const seconds = safeMs / 1000;
  const precision = seconds < 10 ? 2 : 1;
  return `${seconds.toFixed(precision)} detik`;
}

export function ChatAssistantPanel() {
  // Inisialisasi dengan pesan default — sama di server & client (tidak pakai sessionStorage)
  const [messages, setMessages] = useState<ChatMessage[]>([
    createMessage("assistant", CHAT_INITIAL_ASSISTANT_MESSAGE),
  ]);
  // hydrated = true setelah komponen mount di browser
  const [hydrated, setHydrated] = useState(false);
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Setelah mount: load dari sessionStorage (client-only)
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(CHAT_SESSION_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as ChatMessage[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
        }
      }
    } catch {}
    setHydrated(true);
  }, []);

  // Simpan ke sessionStorage setiap kali messages berubah (hanya setelah hydrated)
  useEffect(() => {
    if (hydrated) saveChatHistory(messages);
  }, [messages, hydrated]);

  // Auto-scroll ke bawah
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const q = question.trim();
    if (!q || isSubmitting) return;

    setMessages((prev) => [...prev, createMessage("user", q)]);
    setQuestion("");
    setError(null);
    setIsSubmitting(true);
    const startedAt = performance.now();

    try {
      const res = await fetch(routes.api.pharmacy.chat, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ question: q, user_id: "pharmacy-web-ui" }),
      });
      const body = (await res.json().catch(() => null)) as unknown;
      const elapsedMs = Math.round(performance.now() - startedAt);
      if (!res.ok) {
        const msg =
          isObject(body) &&
          (readText(body.detail) || readText(body.error) || readText(body.message));
        throw new Error(msg || "Gagal mengambil jawaban dari backend.");
      }
      if (!isObject(body)) throw new Error("Format respons tidak sesuai.");
      const answer =
        readText(body.answer) ||
        readText(body.response) ||
        readText(body.message) ||
        "Belum ada jawaban.";
      const cleanedAnswer = normalizeAssistantContent(answer);
      setMessages((prev) => [
        ...prev,
        createMessage("assistant", cleanedAnswer, {
          toolUsed: readText(body.tool_used),
          modelName: readText(body.model_name),
          responseTimeMs: elapsedMs,
        }),
      ]);
    } catch (err) {
      const elapsedMs = Math.round(performance.now() - startedAt);
      const msg = err instanceof Error ? err.message : "Terjadi gangguan.";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        createMessage("assistant", `Error: ${msg}`, {
          responseTimeMs: elapsedMs,
        }),
      ]);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-120px)] flex-col gap-0 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-100 px-6 py-4">
        <h2 className="text-lg font-bold text-slate-900">AI Pharmacy Assistant</h2>
        <p className="text-sm text-slate-500">
          Tanyakan apa saja tentang stok, harga, kadaluarsa, atau informasi obat.
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-0 overflow-y-auto bg-white">
        {messages.map((message) => {
          const isUser = message.role === "user";
          return (
            <article
              key={message.id}
              className="group px-8 py-5 text-base"
            >
              <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
                <div
                  className={`flex w-full max-w-[820px] gap-4 ${
                    isUser ? "flex-row-reverse" : "flex-row"
                  }`}
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full shadow-sm ring-1 ring-slate-100">
                    {isUser ? (
                      <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-600 text-white">
                        <User className="h-5 w-5" />
                      </div>
                    ) : (
                      <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-white">
                        <Sparkles className="h-5 w-5" />
                      </div>
                    )}
                  </div>

                  <div
                    className={`min-w-0 flex flex-col gap-2 ${
                      isUser ? "items-end text-right" : "items-start text-left"
                    }`}
                  >
                    <div
                      className={`flex items-center gap-2 ${
                        isUser ? "justify-end" : "justify-start"
                      }`}
                    >
                      <span className="font-bold text-slate-900">
                        {isUser ? "Anda" : "Pharmasi AI"}
                      </span>
                      {hydrated && (
                        <span className="text-[11px] font-medium text-slate-400 opacity-0 transition-opacity group-hover:opacity-100">
                          {formatTime(message.timestamp)}
                        </span>
                      )}
                    </div>

                    <div
                      className={`rounded-2xl px-4 py-3 shadow-sm ring-1 ${
                        isUser
                          ? "bg-blue-50/70 ring-blue-100"
                          : "bg-white ring-slate-100"
                      }`}
                    >
                      <MessageContent content={message.content} isUser={isUser} />
                    </div>

                    {!isUser &&
                      (message.toolUsed || message.modelName || message.responseTimeMs != null) && (
                      <div className="mt-1 flex flex-wrap gap-2">
                        {message.responseTimeMs != null && (
                          <span className="inline-flex items-center gap-1 rounded-md bg-white border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-500 shadow-sm">
                            <Clock className="h-3 w-3" />
                            Respon: {formatDurationMs(message.responseTimeMs)}
                          </span>
                        )}
                        {message.toolUsed && (
                          <span className="inline-flex items-center gap-1 rounded-md bg-white border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-500 shadow-sm">
                            <Bot className="h-3 w-3" />
                            Tool: {message.toolUsed}
                          </span>
                        )}
                        {message.modelName && (
                          <span className="inline-flex items-center gap-1 rounded-md bg-white border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-500 shadow-sm">
                            <Sparkles className="h-3 w-3 text-emerald-500" />
                            {message.modelName}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </article>
          );
        })}

        {/* Loading bubble */}
        {isSubmitting && (
          <article className="px-8 py-5 text-base">
            <div className="flex w-full justify-start">
              <div className="flex w-full max-w-[820px] gap-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 text-white shadow-sm ring-1 ring-slate-100">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex flex-col gap-2">
                  <span className="font-bold text-slate-900">Pharmasi AI</span>
                  <div className="rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-slate-100">
                    <div className="flex items-center gap-2 text-emerald-600">
                      <div className="flex gap-1.5">
                        <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-500 [animation-delay:-0.3s]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-500 [animation-delay:-0.15s]" />
                        <span className="h-2 w-2 animate-bounce rounded-full bg-emerald-500" />
                      </div>
                      <span className="text-sm font-medium animate-pulse ml-2">Sedang berpikir...</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </article>
        )}

        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="pharmacy-alert pharmacy-alert--error mx-6 mb-2 shrink-0">{error}</div>
      )}

      {/* Input */}
      <div className="shrink-0 border-t border-slate-100 bg-slate-50 px-6 py-4">
        <form onSubmit={handleSend} className="flex items-end gap-3">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ketik pertanyaan farmasi..."
            rows={2}
            className="pharmacy-input flex-1 resize-none text-base"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="pharmacy-button-primary pharmacy-button-primary--sky shrink-0 px-5 py-3 disabled:opacity-50"
          >
            {isSubmitting ? (
              <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
            ) : (
              <svg
                className="h-5 w-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
          </button>
        </form>
        <p className="mt-1.5 text-xs text-slate-400">Enter untuk kirim · Shift+Enter untuk baris baru</p>
      </div>
    </div>
  );
}
