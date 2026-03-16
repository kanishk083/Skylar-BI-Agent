import { useState, useRef, useEffect } from "react";
import { streamChat, pingBackend, fetchBriefing } from "../api";
import Message from "./Message";

const SUGGESTED = [
  { text: "Which deals are at risk?" },
  { text: "What's our total pipeline value?" },
  { text: "Show me overdue work orders" },
  { text: "What's the revenue forecast this month?" },
  { text: "Any anomalies in the deal funnel?" },
];

// Chat is a controlled component — messages + session are owned by App
export default function Chat({ convId, sessionId, initialMessages, onMessagesChange }) {
  const [messages, setMessages]   = useState(initialMessages || []);
  const [input, setInput]         = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError]         = useState("");
  const [warming, setWarming]     = useState(false);
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  // Sync messages up to App (for localStorage persistence)
  useEffect(() => {
    onMessagesChange?.(convId, messages);
  }, [messages]);          // eslint-disable-line react-hooks/exhaustive-deps

  // Patch 6: ping backend on first mount
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const start = Date.now();
      const ok    = await pingBackend();
      if (!cancelled && (!ok || Date.now() - start > 3000)) {
        setWarming(true);
        setTimeout(() => setWarming(false), 60000);
      }
    };
    check();
    return () => { cancelled = true; };
  }, []);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const updateMessages = (updater) => {
    setMessages(prev => {
      const next = typeof updater === "function" ? updater(prev) : updater;
      return next;
    });
  };

  const send = async (query) => {
    if (!query.trim() || streaming) return;
    setError("");
    setInput("");

    const userMsg  = { role: "user",      content: query };
    const agentRef = { role: "assistant", content: "" };

    updateMessages(m => [...m, userMsg, { ...agentRef }]);
    setStreaming(true);

    let accumulated = "";

    await streamChat(
      sessionId,
      query,
      (chunk) => {
        accumulated += chunk;
        updateMessages(m => {
          const updated = [...m];
          updated[updated.length - 1] = { role: "assistant", content: accumulated };
          return updated;
        });
      },
      () => {
        setStreaming(false);
        setTimeout(() => inputRef.current?.focus(), 100);
      },
      (errMsg) => {
        setError(errMsg);
        setStreaming(false);
        updateMessages(m => m.slice(0, -1)); // remove empty assistant bubble
      }
    );
  };

  const loadBriefing = async () => {
    if (streaming) return;
    setError("");
    setStreaming(true);

    updateMessages(m => [
      ...m,
      { role: "user",      content: "Morning Briefing" },
      { role: "assistant", content: "" },
    ]);

    let content = "";
    await fetchBriefing(
      (chunk) => {
        content += chunk;
        updateMessages(m => {
          const updated = [...m];
          updated[updated.length - 1] = { role: "assistant", content };
          return updated;
        });
      },
      () => setStreaming(false),
      (errMsg) => {
        setError(errMsg);
        setStreaming(false);
      }
    );
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full bg-skylark-cream">

      {/* Alerts */}
      {warming && (
        <div className="mx-6 mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg py-2 px-4 flex items-center gap-2">
          <span>⏳</span> Backend warming up — up to 60s on first request
        </div>
      )}
      {error && (
        <div className="mx-6 mt-3 text-xs text-red-700 bg-red-50 border border-red-200 rounded-lg py-2 px-4 flex items-center gap-2">
          <span>⚠️</span> {error}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isEmpty ? (
          <EmptyState onSuggest={send} onBriefing={loadBriefing} />
        ) : (
          <div className="max-w-3xl mx-auto space-y-1 pb-2">
            {messages.map((m, i) => (
              <Message
                key={i}
                role={m.role}
                content={m.content}
                isStreaming={streaming && i === messages.length - 1 && m.role === "assistant"}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-skylark-border bg-white px-6 py-4 flex-shrink-0">
        <div className="max-w-3xl mx-auto">
          {/* Quick chips when conversation has messages */}
          {!isEmpty && !streaming && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {SUGGESTED.slice(0, 3).map((q) => (
                <button
                  key={q.text}
                  onClick={() => send(q.text)}
                  className="text-[11px] px-2.5 py-1 border border-skylark-border rounded-full text-skylark-brown
                    hover:bg-skylark-orange-light hover:border-skylark-orange/40 hover:text-skylark-orange transition-all"
                >
                  {q.text}
                </button>
              ))}
            </div>
          )}

          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(input);
                  }
                }}
                placeholder="Ask about pipeline, deals, work orders…"
                disabled={streaming}
                rows={1}
                className="w-full bg-white border border-skylark-border rounded-xl px-4 py-3 text-sm text-skylark-dark
                  placeholder-gray-400 focus:outline-none focus:border-skylark-orange/60 focus:ring-2 focus:ring-skylark-orange/15
                  disabled:opacity-50 disabled:cursor-not-allowed min-h-[46px] max-h-32 overflow-y-auto leading-snug transition-all"
                style={{ resize: "none" }}
              />
            </div>
            <button
              onClick={() => send(input)}
              disabled={streaming || !input.trim()}
              className="btn-orange text-white rounded-xl px-5 py-3 text-sm font-medium flex items-center gap-2 flex-shrink-0 h-[46px]"
            >
              {streaming ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Thinking
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  Send
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </span>
              )}
            </button>
          </div>
          <p className="text-[10px] text-gray-400 mt-2 text-center">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────
function EmptyState({ onSuggest, onBriefing }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[58vh] text-center px-4">
      <div className="w-20 h-20 rounded-2xl bg-skylark-orange/10 border border-skylark-orange/20 flex items-center justify-center mb-5">
        <svg viewBox="0 0 48 34" className="w-12 h-12 text-skylark-orange" fill="none">
          <rect x="17" y="13" width="14" height="8" rx="3" fill="currentColor" opacity="0.9"/>
          <circle cx="24" cy="17" r="2.5" fill="#1A0D06"/>
          <line x1="17" y1="14.5" x2="6"  y2="5"   stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/>
          <line x1="31" y1="14.5" x2="42" y2="5"   stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/>
          <line x1="17" y1="19.5" x2="6"  y2="29"  stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/>
          <line x1="31" y1="19.5" x2="42" y2="29"  stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"/>
          <ellipse cx="6"  cy="4"  rx="5.5" ry="2" fill="currentColor" opacity="0.7"/>
          <ellipse cx="42" cy="4"  rx="5.5" ry="2" fill="currentColor" opacity="0.7"/>
          <ellipse cx="6"  cy="30" rx="5.5" ry="2" fill="currentColor" opacity="0.7"/>
          <ellipse cx="42" cy="30" rx="5.5" ry="2" fill="currentColor" opacity="0.7"/>
        </svg>
      </div>

      <h2 className="text-2xl font-bold text-skylark-dark tracking-tight">
        SKY<span className="text-skylark-orange">LARK</span> BI Agent
      </h2>
      <p className="text-gray-500 text-sm mt-1.5 max-w-sm leading-relaxed">
        Your Monday.com-powered intelligence layer. Ask anything about your pipeline, deals, or work orders.
      </p>

      <button
        onClick={onBriefing}
        className="mt-5 btn-orange text-white rounded-xl px-6 py-2.5 text-sm font-semibold"
      >
        Morning Briefing
      </button>

      <div className="mt-7 w-full max-w-lg">
        <p className="text-xs text-gray-400 uppercase tracking-widest font-medium mb-3">
          Suggested queries
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {SUGGESTED.map((q) => (
            <button
              key={q.text}
              onClick={() => onSuggest(q.text)}
              className="flex items-center text-left px-4 py-3 bg-white border border-skylark-border rounded-xl
                hover:border-skylark-orange/50 hover:bg-skylark-orange-light hover:shadow-sm
                text-sm text-skylark-dark transition-all duration-150 group"
            >
              <span className="group-hover:text-skylark-orange transition-colors">{q.text}</span>
            </button>
          ))}
        </div>
      </div>

      <p className="text-[11px] text-gray-300 mt-8">
        Skylark Drones · Spectra Platform · BI Intelligence Layer
      </p>
    </div>
  );
}
