import { useState } from "react";
import type { AnalyzeResponse } from "../types";
import DecisionBadge from "./DecisionBadge";
import SuggestedReply from "./SuggestedReply";
import EvidencePanel from "./EvidencePanel";
import SafetyChecklist from "./SafetyChecklist";
import { ChevronIcon } from "./Icons";

interface AnalysisResultProps {
  result: AnalyzeResponse;
}

export default function AnalysisResult({ result }: AnalysisResultProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [safetyOpen, setSafetyOpen] = useState(false);

  return (
    <div className="assistant-card">
      <div className="stat-row">
        <div className="stat">
          <span className="stat-label">Intent</span>
          <span className="stat-value">{result.intent}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Confidence</span>
          <span className="stat-value">{Math.round(result.confidence * 100)}%</span>
        </div>
      </div>

      <SuggestedReply reply={result.reply} />

      <div className="subsection">
        <span className="stat-label">Recommended action</span>
        <div className="action-value">
          <DecisionBadge decision={result.decision} />
        </div>
      </div>

      <div className="subsection">
        <span className="stat-label">Reason</span>
        <p>{result.reason}</p>
      </div>

      <div className="section-toggles">
        <button
          type="button"
          className={`pill-toggle ${evidenceOpen ? "active" : ""}`}
          onClick={() => setEvidenceOpen((prev) => !prev)}
          aria-expanded={evidenceOpen}
        >
          Historical evidence
          <ChevronIcon className={`chevron ${evidenceOpen ? "expanded" : ""}`} />
        </button>
        <button
          type="button"
          className={`pill-toggle ${safetyOpen ? "active" : ""}`}
          onClick={() => setSafetyOpen((prev) => !prev)}
          aria-expanded={safetyOpen}
        >
          Safety checks
          <ChevronIcon className={`chevron ${safetyOpen ? "expanded" : ""}`} />
        </button>
      </div>

      {evidenceOpen && <EvidencePanel evidence={result.evidence} />}
      {safetyOpen && <SafetyChecklist safetyChecks={result.safety_checks} />}
    </div>
  );
}
