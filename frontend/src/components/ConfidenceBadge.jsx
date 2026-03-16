// ConfidenceBadge — Skylark Drones theme
const styles = {
  high:   "bg-green-50  text-green-700  border-green-200",
  medium: "bg-amber-50  text-amber-700  border-amber-200",
  low:    "bg-red-50    text-red-600    border-red-200",
};

const dots = {
  high:   "bg-green-500",
  medium: "bg-amber-500",
  low:    "bg-red-500",
};

export default function ConfidenceBadge({ level }) {
  if (!level) return null;
  const key = level.toLowerCase();
  return (
    <span className={`inline-flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-full border font-medium ${styles[key] || styles.medium}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dots[key] || dots.medium}`} />
      {key.charAt(0).toUpperCase() + key.slice(1)} confidence
    </span>
  );
}
