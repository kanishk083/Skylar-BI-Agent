// Message.jsx — Skylark Drones branded chat bubbles

// Very minimal markdown renderer (bold, bullet lists, newlines)
function renderContent(text) {
  if (!text) return null;

  const lines = text.split("\n");
  const elements = [];
  let listItems = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="my-1.5 pl-4 space-y-0.5 list-disc">
          {listItems.map((item, i) => (
            <li key={i} className="leading-snug">{renderInline(item)}</li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Bullet list
    if (/^[-•*]\s+/.test(trimmed)) {
      listItems.push(trimmed.replace(/^[-•*]\s+/, ""));
      return;
    }

    // Numbered list
    if (/^\d+\.\s+/.test(trimmed)) {
      listItems.push(trimmed.replace(/^\d+\.\s+/, ""));
      return;
    }

    flushList();

    if (trimmed === "") {
      if (idx > 0) elements.push(<div key={idx} className="h-1.5" />);
      return;
    }

    // Heading-like lines (all caps short or ending with :)
    if (/^[A-Z][A-Z\s&-]{2,}:?\s*$/.test(trimmed) && trimmed.length < 50) {
      elements.push(
        <p key={idx} className="font-semibold text-skylark-dark mt-2 mb-0.5 text-[13px] uppercase tracking-wide">
          {trimmed.replace(/:$/, "")}
        </p>
      );
      return;
    }

    elements.push(
      <p key={idx} className="leading-relaxed">
        {renderInline(line)}
      </p>
    );
  });

  flushList();
  return elements;
}

function renderInline(text) {
  // **bold** support
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export default function Message({ role, content, isStreaming }) {
  const isUser = role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end mb-3 msg-enter">
        <div className="max-w-[75%] bg-skylark-orange text-white px-4 py-2.5 rounded-2xl rounded-br-sm text-sm leading-relaxed shadow-sm">
          {content}
        </div>
      </div>
    );
  }

  // Assistant bubble
  return (
    <div className="flex justify-start gap-2.5 mb-3 msg-enter">
      {/* Avatar */}
      <div className="w-7 h-7 rounded-full bg-skylark-dark flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
        <svg viewBox="0 0 24 18" className="w-4 h-4 text-skylark-orange" fill="none">
          <rect x="8" y="6" width="8" height="6" rx="2" fill="currentColor" opacity="0.9"/>
          <circle cx="12" cy="9" r="1.5" fill="#1A0D06"/>
          <line x1="8"  y1="7" x2="3"  y2="3"  stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          <line x1="16" y1="7" x2="21" y2="3"  stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          <line x1="8"  y1="11" x2="3"  y2="15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          <line x1="16" y1="11" x2="21" y2="15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          <ellipse cx="3"  cy="2.5"  rx="3" ry="1.2" fill="currentColor" opacity="0.7"/>
          <ellipse cx="21" cy="2.5"  rx="3" ry="1.2" fill="currentColor" opacity="0.7"/>
          <ellipse cx="3"  cy="15.5" rx="3" ry="1.2" fill="currentColor" opacity="0.7"/>
          <ellipse cx="21" cy="15.5" rx="3" ry="1.2" fill="currentColor" opacity="0.7"/>
        </svg>
      </div>

      {/* Bubble */}
      <div className="max-w-[78%] bg-white border border-skylark-border rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-skylark-dark shadow-sm">
        {content ? (
          <div className="prose-skylark space-y-0">
            {renderContent(content)}
          </div>
        ) : null}
        {isStreaming && <span className="cursor-blink" />}
      </div>
    </div>
  );
}
