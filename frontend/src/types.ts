export type Decision = "auto_handle" | "escalate";

export interface EvidenceItem {
  id: string;
  customer_text: string;
  agent_reply: string;
  similarity: number; 
}

export interface SafetyChecks {
  grounded_in_evidence: boolean;
  invents_policy?: boolean;
  invents_refund_or_compensation?: boolean;
  invents_delivery_date?: boolean;
  invents_account_action?: boolean;
  contains_pii?: boolean;
  fallback?: boolean;
  dev_fallback?: boolean;
  [key: string]: unknown;
}

/** Request body for POST /analyze. */
export interface AnalyzeRequest {
  customer_message: string;
  brand: string;
}

/** Full response from POST /analyze. */
export interface AnalyzeResponse {
  intent: string;
  confidence: number; // 0-1
  reply: string;
  decision: Decision;
  reason: string;
  evidence: EvidenceItem[]; 
  safety_checks: SafetyChecks;
}
