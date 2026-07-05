"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { User, Sparkles, Clock } from "lucide-react";
import { routes } from "@/lib/constants/routes";
import { getAuthHeader } from "@/lib/api/client";

type ChatRole = "user" | "assistant";

interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: number;
  responseTimeMs?: number;
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

function normalizeContent(content: string): string {
  return content
    .replace(/<unused\d+>thought[\s\S]*?(?:<unused\d+>|$)/g, "")
    .replace(/<unused\d+>/g, "")
    .replace(/```json[\s\S]*?```/gi, (block) => (/["']tool["']\s*:/.test(block) ? "" : block))
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function formatDurationMs(ms: number): string {
  if (!Number.isFinite(ms)) return "-";
  const safeMs = Math.max(0, ms);
  const seconds = safeMs / 1000;
  const precision = seconds < 10 ? 2 : 1;
  return `${seconds.toFixed(precision)} detik`;
}

function MessageContent({ content, isUser }: { content: string; isUser: boolean }) {
  if (isUser) {
    return <p className="leading-relaxed whitespace-pre-wrap text-slate-800">{content}</p>;
  }
  return (
    <div className="space-y-2">
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed text-slate-800">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
          ul: ({ children }) => <ul className="mb-2 ml-5 list-disc space-y-1 text-slate-800">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2 ml-5 list-decimal space-y-1 text-slate-800">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed pl-1">{children}</li>,
          h3: ({ children }) => <h3 className="mb-1 mt-3 text-base font-semibold text-slate-900">{children}</h3>,
          code: ({ children }) => <code className="rounded bg-teal-50 px-1.5 py-0.5 text-[13px] font-mono text-teal-700">{children}</code>,
        }}
      >
        {normalizeContent(content) || "Memproses..."}
      </ReactMarkdown>
    </div>
  );
}

const INITIAL_MESSAGE = createMessage(
  "assistant",
  "Halo! Saya asisten informasi obat Anda. Tanyakan apa saja tentang obat, dosis, efek samping, atau cara penggunaan. Saya siap membantu! 💊"
);

function getSessionKey(uid: string): string {
  return `patient_chat_${uid}`;
}

function buildInitialMessage(simrsData: any): ChatMessage {
  if (simrsData?.nama) {
    return createMessage(
      "assistant",
      `Halo, **${simrsData.nama}**! Saya asisten informasi obat Anda. Silakan tanyakan apa saja seputar obat atau kondisi Anda, saya siap membantu! 💊`
    );
  }
  return createMessage(
    "assistant",
    "Halo! Saya asisten informasi obat Anda. Silakan tanyakan apa saja seputar obat atau kondisi Anda, saya siap membantu! 💊"
  );
}

export function PatientChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [hydrated, setHydrated] = useState(false);
  const [hasChatHistory, setHasChatHistory] = useState(false);
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState("patient_user");
  const [userRole, setUserRole] = useState("patient");
  const [simrsData, setSimrsData] = useState<any>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem("pharmacy_user");
      let resolvedUserId = "patient_user";
      if (stored) {
        const parsed = JSON.parse(stored);
        if (parsed.id) {
          resolvedUserId = parsed.id;
          setUserId(parsed.id);
        }
        if (parsed.role) setUserRole(parsed.role);
        // Fetch data SIM RS pasien untuk konteks AI
        if (parsed.nik) {
          fetch(`${routes.api.health.replace('/health', '')}/simrs/${parsed.nik}`, { headers: getAuthHeader() })
            .then(res => res.ok ? res.json() : null)
            .then(data => { if (data) setSimrsData(data); })
            .catch(() => {});
        }
      }
      // Load chat history untuk user ini saja (key berbasis user ID)
      const sessionKey = getSessionKey(resolvedUserId);
      const raw = sessionStorage.getItem(sessionKey);
      if (raw) {
        const parsed = JSON.parse(raw) as ChatMessage[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          setMessages(parsed);
          setHasChatHistory(true);
        }
      }
    } catch {}
    setHydrated(true);
  }, []);

  // Update salam awal dengan data SIM RS jika belum ada riwayat chat
  useEffect(() => {
    if (simrsData && !hasChatHistory) {
      setMessages([buildInitialMessage(simrsData)]);
    }
  }, [simrsData, hasChatHistory]);

  useEffect(() => {
    if (hydrated) {
      try {
        sessionStorage.setItem(getSessionKey(userId), JSON.stringify(messages));
      } catch {}
    }
  }, [messages, hydrated, userId]);

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
      const res = await fetch(routes.api.patient.chat, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ 
          question: q, 
          user_id: userId, 
          patient_context: simrsData || null,
        }),
      });
      const body = await res.json().catch(() => null) as Record<string, unknown> | null;
      const elapsedMs = Math.round(performance.now() - startedAt);

      if (!res.ok) {
        const msg = typeof body?.detail === "string" ? body.detail : "Gagal mendapatkan jawaban.";
        throw new Error(msg);
      }

      const answer = typeof body?.answer === "string" ? body.answer : "Belum ada jawaban.";
      setMessages((prev) => [
        ...prev,
        createMessage("assistant", answer, { responseTimeMs: elapsedMs }),
      ]);
    } catch (err) {
      const elapsedMs = Math.round(performance.now() - startedAt);
      const msg = err instanceof Error ? err.message : "Terjadi gangguan.";
      setError(msg);
      setMessages((prev) => [
        ...prev,
        createMessage("assistant", `Maaf, terjadi kesalahan: ${msg}`, { responseTimeMs: elapsedMs }),
      ]);
    } finally {
      setIsSubmitting(false);
    }
  }

  function formatTime(ts: number): string {
    return new Intl.DateTimeFormat("id-ID", { hour: "2-digit", minute: "2-digit" }).format(new Date(ts));
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      {/* Header */}
      <div className="shrink-0 border-b border-slate-100 bg-gradient-to-r from-teal-50 to-emerald-50 px-6 py-4">
        <div className="flex items-center gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-900">Asisten Patient</h2>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-0 overflow-y-auto bg-white">
        {messages.map((message) => {
          const isUser = message.role === "user";
          return (
            <article
              key={message.id}
              className="group px-8 py-5 text-base border-b border-slate-50/50"
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
                      <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-emerald-600 text-white">
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
                        {isUser ? "Pasien" : "Asisten AI"}
                      </span>
                      {hydrated && (
                        <span className="text-xs font-medium text-slate-400 select-none">
                          {formatTime(message.timestamp)}
                        </span>
                      )}
                    </div>

                    <div className="prose prose-slate max-w-none text-sm text-slate-800">
                      <MessageContent content={message.content} isUser={isUser} />
                    </div>

                    {!isUser && message.responseTimeMs != null && (
                      <div className="mt-1 flex flex-wrap gap-2">
                        <span className="inline-flex items-center gap-1 rounded-md bg-white border border-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-500 shadow-sm">
                          <Clock className="h-3 w-3" />
                          Respon: {formatDurationMs(message.responseTimeMs)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </article>
          );
        })}

        {/* Loading */}
        {isSubmitting && (
          <article className="group px-8 py-5 text-base border-b border-slate-50/50">
            <div className="flex w-full justify-start">
              <div className="flex w-full max-w-[820px] gap-4 flex-row">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full shadow-sm ring-1 ring-slate-100">
                  <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-teal-500 to-emerald-600 text-white">
                    <Sparkles className="h-5 w-5 animate-pulse" />
                  </div>
                </div>
                <div className="min-w-0 flex flex-col gap-2 items-start text-left pt-2">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-teal-500 [animation-delay:-0.3s]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-teal-500 [animation-delay:-0.15s]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-teal-500" />
                  </div>
                </div>
              </div>
            </div>
          </article>
        )}

        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mx-4 mb-2 shrink-0 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="shrink-0 border-t border-slate-200 bg-white px-4 py-3">
        <form onSubmit={handleSend} className="flex items-end gap-2">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Tanyakan tentang obat, dosis, efek samping..."
            rows={2}
            className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none transition focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                e.currentTarget.form?.requestSubmit();
              }
            }}
          />
          <button
            type="submit"
            disabled={isSubmitting || !question.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-600 text-white transition hover:bg-teal-700 disabled:opacity-50"
          >
            {isSubmitting ? (
              <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </form>
        <p className="mt-1 text-[10px] text-slate-400">Enter untuk kirim · Shift+Enter untuk baris baru</p>
      </div>
    </div>
  );
}
