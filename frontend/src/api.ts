import type { AnalyzeRequest, AnalyzeResponse } from "./types";

// Base URL of the FastAPI backend, injected by Vite at build time.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/**
 * Sends a customer message (for a given brand) to the backend and returns
 * the agent's evidence-grounded decision, reply, and supporting evidence.
 */
export async function analyzeMessage(customerMessage: string, brand: string): Promise<AnalyzeResponse> {
  const payload: AnalyzeRequest = { customer_message: customerMessage, brand };

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Analysis request failed: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as AnalyzeResponse;
}
