import type { ReactNode } from "react";

const URL_SPLIT_RE = /(https?:\/\/[^\s]+)/g;
const URL_TEST_RE = /^https?:\/\/[^\s]+$/;

/**
 * Splits `text` on URLs and renders each URL as a clickable link, opening
 * in a new tab. Plain text segments are rendered as-is.
 */
export function linkify(text: string): ReactNode[] {
  return text.split(URL_SPLIT_RE).map((part, i) =>
    URL_TEST_RE.test(part) ? (
      // eslint-disable-next-line react/no-array-index-key -- segments are stable for a given reply/evidence string
      <a key={i} href={part} target="_blank" rel="noopener noreferrer">
        {part}
      </a>
    ) : (
      part
    ),
  );
}

// Matches a trailing agent-initials signature, e.g. " ^ZW" or "^RR" at the
// very end of a historical reply — an internal convention from the raw
// dataset, not something a customer-facing summary should show.
const AGENT_SIGNATURE_RE = /\s*\^[A-Z]{1,3}\s*$/;

/** Strips a trailing "^XY"-style agent-initials signature, if present. */
export function stripAgentSignature(text: string): string {
  return text.replace(AGENT_SIGNATURE_RE, "").trim();
}
