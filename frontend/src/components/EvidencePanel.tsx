import type { EvidenceItem } from "../types";
import { linkify, stripAgentSignature } from "../utils/text";

const MAX_SHOWN = 3;

export default function EvidencePanel({ evidence }: { evidence: EvidenceItem[] }) {
  const shown = evidence.slice(0, MAX_SHOWN);

  if (shown.length === 0) {
    return <p className="muted subsection">No similar past conversations were found.</p>;
  }

  return (
    <ul className="evidence-list subsection">
      {shown.map((item) => (
        <li key={item.id} className="evidence-item">
          <p className="evidence-line">
            <strong>Customer message:</strong> {linkify(item.customer_text)}
          </p>
          <p className="evidence-line">
            <strong>Historical response:</strong> {linkify(stripAgentSignature(item.agent_reply))}
          </p>
          <p className="evidence-meta">relevance: {Math.round(item.similarity * 100)}%</p>
        </li>
      ))}
    </ul>
  );
}
