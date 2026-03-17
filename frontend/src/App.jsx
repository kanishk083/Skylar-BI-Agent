import { useState, useEffect, useCallback } from "react";
import { v4 as uuid } from "uuid";
import Chat from "./components/Chat";

// ─── localStorage helpers ────────────────────────────────────────────────────
const LS_KEY = "skylark_conversations";

function loadConversations() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveConversations(convs) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(convs));
  } catch { /* storage full — ignore */ }
}

function newConversation() {
  return { id: uuid(), sessionId: uuid(), title: "New chat", messages: [], createdAt: Date.now() };
}

// ─── Date grouping ───────────────────────────────────────────────────────────
function groupByDate(convs) {
  const now   = Date.now();
  const day   = 86400000;
  const today     = [];
  const yesterday = [];
  const last7     = [];
  const older     = [];

  for (const c of [...convs].reverse()) {
    const diff = now - c.createdAt;
    if (diff < day)         today.push(c);
    else if (diff < 2*day)  yesterday.push(c);
    else if (diff < 7*day)  last7.push(c);
    else                    older.push(c);
  }
  return [
    { label: "Today",           items: today },
    { label: "Yesterday",       items: yesterday },
    { label: "Previous 7 days", items: last7 },
    { label: "Older",           items: older },
  ].filter(g => g.items.length > 0);
}

// ─── Icons ───────────────────────────────────────────────────────────────────
function DroneIcon({ className = "" }) {
  return (
    <svg className={className} viewBox="0 0 40 28" fill="none">
      <rect x="14" y="11" width="12" height="6" rx="2" fill="currentColor" />
      <circle cx="20" cy="14" r="2" fill="#1E1008" />
      <line x1="14" y1="12" x2="5"  y2="5"  stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="26" y1="12" x2="35" y2="5"  stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="14" y1="16" x2="5"  y2="23" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <line x1="26" y1="16" x2="35" y2="23" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <ellipse cx="5"  cy="4"  rx="4.5" ry="1.5" fill="currentColor" opacity="0.8" />
      <ellipse cx="35" cy="4"  rx="4.5" ry="1.5" fill="currentColor" opacity="0.8" />
      <ellipse cx="5"  cy="24" rx="4.5" ry="1.5" fill="currentColor" opacity="0.8" />
      <ellipse cx="35" cy="24" rx="4.5" ry="1.5" fill="currentColor" opacity="0.8" />
    </svg>
  );
}

function IconPencil() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  );
}

function IconTrash() {
  return (
    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  );
}

function IconRefresh() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  );
}

function IconChat() {
  return (
    <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

// ─── Stat chip ───────────────────────────────────────────────────────────────
function StatChip({ label, value, trend }) {
  return (
    <div className="bg-white/5 rounded-lg px-3 py-2.5 border border-white/[0.08]">
      <p className="text-white/40 text-[10px] uppercase tracking-widest font-medium">{label}</p>
      <p className="text-white font-semibold text-sm mt-0.5">{value}</p>
      {trend && (
        <p className={`text-[10px] mt-0.5 ${trend.startsWith("+") ? "text-green-400" : "text-red-400"}`}>
          {trend}
        </p>
      )}
    </div>
  );
}

// ─── App ─────────────────────────────────────────────────────────────────────
export default function App() {
  const [conversations, setConversations] = useState(() => {
    const saved = loadConversations();
    if (saved.length === 0) {
      const fresh = newConversation();
      return [fresh];
    }
    return saved;
  });

  const [activeId, setActiveId] = useState(() => {
    const saved = loadConversations();
    return saved.length > 0 ? saved[saved.length - 1].id : conversations[0]?.id;
  });

  // Persist to localStorage on every change
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  const activeConv = conversations.find(c => c.id === activeId) || conversations[0];

  // Create a new chat and switch to it
  const handleNewChat = useCallback(() => {
    const conv = newConversation();
    setConversations(prev => [...prev, conv]);
    setActiveId(conv.id);
  }, []);

  // Switch to an existing conversation
  const handleSelect = useCallback((id) => {
    setActiveId(id);
  }, []);

  // Delete a conversation
  const handleDelete = useCallback((id, e) => {
    e.stopPropagation();
    setConversations(prev => {
      const next = prev.filter(c => c.id !== id);
      if (next.length === 0) {
        const fresh = newConversation();
        setActiveId(fresh.id);
        return [fresh];
      }
      if (id === activeId) {
        setActiveId(next[next.length - 1].id);
      }
      return next;
    });
  }, [activeId]);

  // Chat updates messages — save back + auto-title from first user message
  const handleMessagesChange = useCallback((convId, messages) => {
    setConversations(prev => prev.map(c => {
      if (c.id !== convId) return c;
      // Auto-title: first user message, max 42 chars
      const firstUser = messages.find(m => m.role === "user");
      const title = firstUser
        ? firstUser.content.slice(0, 42) + (firstUser.content.length > 42 ? "…" : "")
        : "New chat";
      return { ...c, messages, title };
    }));
  }, []);

  // Refresh = start a new chat
  const handleRefresh = useCallback(() => {
    handleNewChat();
  }, [handleNewChat]);

  const groups = groupByDate(conversations);

  return (
    <div className="flex h-screen overflow-hidden bg-skylark-cream font-sans">

      {/* ─── Sidebar ──────────────────────────────────────── */}
      <aside className="w-64 flex-shrink-0 bg-skylark-dark flex flex-col overflow-hidden">

        {/* Brand + New Chat button */}
        <div className="px-4 pt-5 pb-4 border-b border-white/[0.08]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-skylark-orange/20 flex items-center justify-center flex-shrink-0">
                <DroneIcon className="w-5 h-5 text-skylark-orange" />
              </div>
              <div>
                <p className="text-white font-bold text-[13px] tracking-tight leading-tight">
                  SKY<span className="text-skylark-orange">LARK</span>
                </p>
                <p className="text-white/35 text-[9px] uppercase tracking-widest">BI Agent</p>
              </div>
            </div>
          </div>

          {/* New Chat button */}
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 bg-skylark-orange/15 hover:bg-skylark-orange/25
              border border-skylark-orange/30 text-skylark-orange rounded-xl px-3 py-2.5
              text-xs font-semibold transition-all duration-150"
          >
            <IconPencil />
            New Chat
          </button>
        </div>

        {/* Conversation history */}
        <div className="flex-1 overflow-y-auto py-3 px-2">
          {groups.length === 0 ? (
            <p className="text-white/25 text-xs text-center mt-8">No conversations yet</p>
          ) : (
            groups.map(group => (
              <div key={group.label} className="mb-4">
                <p className="text-white/25 text-[9px] uppercase tracking-widest font-semibold px-2 mb-1.5">
                  {group.label}
                </p>
                {group.items.map(conv => (
                  <ConvItem
                    key={conv.id}
                    conv={conv}
                    active={conv.id === activeId}
                    onSelect={handleSelect}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            ))
          )}
        </div>

        {/* Live stats */}
        <div className="px-3 py-3 border-t border-white/[0.08]">
          <p className="text-white/25 text-[9px] uppercase tracking-widest font-semibold px-1 mb-2">
            Live Snapshot
          </p>
          <div className="space-y-1.5">
            <StatChip label="Pipeline"    value="₹68.82 Cr" trend="+12% MoM" />
            <StatChip label="At Risk"     value="43 deals"  />
            <StatChip label="Overdue WOs" value="31 orders" />
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 pb-4 pt-2 border-t border-white/[0.08]">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse flex-shrink-0" />
            <span className="text-white/35 text-[10px] font-medium">monday.com connected</span>
          </div>
          <p className="text-white/20 text-[9px] mt-1">Powered by Groq · llama-3.3-70b</p>
        </div>
      </aside>

      {/* ─── Main content ─────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* Header */}
        <header className="h-14 bg-white border-b border-skylark-border flex items-center justify-between px-6 flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <IconChat />
            <h1 className="text-skylark-dark font-semibold text-sm truncate max-w-xs" title={activeConv?.title}>
              {activeConv?.title || "New chat"}
            </h1>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Refresh / New chat button */}
            <button
              onClick={handleRefresh}
              title="New chat"
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-skylark-orange
                border border-skylark-border hover:border-skylark-orange/40
                px-3 py-1.5 rounded-lg transition-all duration-150 hover:bg-skylark-orange-light"
            >
              <IconRefresh />
              <span className="hidden sm:inline">New chat</span>
            </button>
            <span className="text-xs font-medium text-white bg-skylark-orange px-3 py-1 rounded-full">
              Live
            </span>
          </div>
        </header>

        {/* Chat — keyed by conversation id so it fully remounts on switch */}
        <div className="flex-1 min-h-0" key={activeConv?.id}>
          {activeConv && (
            <Chat
              convId={activeConv.id}
              sessionId={activeConv.sessionId}
              initialMessages={activeConv.messages}
              onMessagesChange={handleMessagesChange}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Conversation list item ───────────────────────────────────────────────────
function ConvItem({ conv, active, onSelect, onDelete }) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      onClick={() => onSelect(conv.id)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-left group transition-all duration-100
        ${active
          ? "bg-white/10 text-white"
          : "text-white/50 hover:bg-white/5 hover:text-white/75"
        }`}
    >
      <IconChat />
      <span className="flex-1 text-xs truncate leading-snug">
        {conv.title}
      </span>
      {/* Delete button — show on hover or active */}
      {(hovered || active) && (
        <span
          role="button"
          onClick={(e) => onDelete(conv.id, e)}
          className="flex-shrink-0 p-1 rounded hover:bg-red-500/20 hover:text-red-400 text-white/30 transition-colors"
          title="Delete conversation"
        >
          <IconTrash />
        </span>
      )}
    </button>
  );
}
