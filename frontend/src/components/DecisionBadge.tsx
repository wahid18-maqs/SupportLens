import type { Decision } from "../types";

const LABELS: Record<Decision, { label: string; className: string }> = {
  auto_handle: { label: "Auto-handle", className: "badge-auto" },
  escalate: { label: "Escalate to human", className: "badge-escalate" },
};

export default function DecisionBadge({ decision }: { decision: Decision }) {
  const { label, className } = LABELS[decision];
  return <span className={`badge ${className}`}>{label}</span>;
}
