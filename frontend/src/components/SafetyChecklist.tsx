import type { SafetyChecks } from "../types";
import { CheckCircleIcon, WarningIcon } from "./Icons";

const CHECKS: { key: keyof SafetyChecks; label: string; safeValue: boolean }[] = [
  { key: "grounded_in_evidence", label: "Reply grounded in historical evidence", safeValue: true },
  { key: "invents_policy", label: "No invented policy", safeValue: false },
  { key: "invents_refund_or_compensation", label: "No invented refund or compensation", safeValue: false },
  { key: "invents_delivery_date", label: "No invented delivery date", safeValue: false },
  { key: "invents_account_action", label: "No invented account action", safeValue: false },
  { key: "contains_pii", label: "No sensitive information requested publicly", safeValue: false },
];


export default function SafetyChecklist({ safetyChecks }: { safetyChecks: SafetyChecks }) {
  const isFallback = Boolean(safetyChecks.fallback ?? safetyChecks.dev_fallback);

  return (
    <div className="subsection">
      {isFallback && (
        <p className="muted safety-fallback-note">
          This is a safe fallback response — no language model call was trusted for this result.
        </p>
      )}
      <ul className="safety-list">
        {CHECKS.map(({ key, label, safeValue }) => {
          const value = safetyChecks[key];
          const passed = typeof value === "boolean" ? value === safeValue : undefined;
          return (
            <li key={key} className={`safety-item ${passed === undefined ? "unknown" : passed ? "pass" : "fail"}`}>
              {passed === true ? <CheckCircleIcon /> : <WarningIcon />}
              <span>{label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
