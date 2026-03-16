const QUERIES = [
  "Which deals are at risk?",
  "What's our total pipeline value?",
  "Show me overdue work orders",
  "What's the revenue forecast this month?",
  "Any anomalies in the deal funnel?",
];

export default function SuggestedQueries({ onSelect }) {
  return (
    <div className="flex flex-wrap gap-2 justify-center">
      {QUERIES.map((q) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          className="text-xs px-3 py-1.5 border border-gray-200 rounded-full hover:bg-gray-50 text-gray-600 transition-colors"
        >
          {q}
        </button>
      ))}
    </div>
  );
}
