import { useLayoutEffect, useRef, useState } from "react";
import WelcomeScreen from "./components/WelcomeScreen";
import UserMessageBubble from "./components/UserMessageBubble";
import AnalysisResult from "./components/AnalysisResult";
import ChatInput from "./components/ChatInput";
import BrandHeader from "./components/BrandHeader";
import { analyzeMessage } from "./api";
import type { AnalyzeResponse } from "./types";

const DEFAULT_BRAND = "AmazonHelp";

interface Turn {
  id: string;
  message: string;
  result: AnalyzeResponse | null;
  error: string | null;
  loading: boolean;
}

export default function App() {
  const [message, setMessage] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const isChat = turns.length > 0;

  // FLIP animation: capture the header's centered position right before the
  // first message switches the layout to compact/top-left, then let the
  // browser paint the new (already-compact) layout, and finally animate
  // from the old position/size to the new one via a transform — cheaper
  // than a layout-animation library for a single one-shot transition.
  const headerRef = useRef<HTMLDivElement>(null);
  const preSubmitRectRef = useRef<DOMRect | null>(null);

  useLayoutEffect(() => {
    const el = headerRef.current;
    const first = preSubmitRectRef.current;
    if (!el || !first) return;
    preSubmitRectRef.current = null;

    const last = el.getBoundingClientRect();
    const dx = first.left - last.left;
    const dy = first.top - last.top;
    const scaleX = first.width / last.width;
    const scaleY = first.height / last.height;

    el.style.transformOrigin = "top left";
    el.style.transition = "none";
    el.style.transform = `translate(${dx}px, ${dy}px) scale(${scaleX}, ${scaleY})`;

    requestAnimationFrame(() => {
      el.style.transition = "transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)";
      el.style.transform = "";
    });
  }, [isChat]);

  const handleSubmit = async (customerMessage: string, brand: string) => {
    if (!isChat && headerRef.current) {
      preSubmitRectRef.current = headerRef.current.getBoundingClientRect();
    }

    const id = crypto.randomUUID();
    setTurns((prev) => [...prev, { id, message: customerMessage, result: null, error: null, loading: true }]);
    setMessage("");

    try {
      const response = await analyzeMessage(customerMessage, brand);
      setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, result: response, loading: false } : t)));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Something went wrong. Please try again.";
      setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, error: errorMessage, loading: false } : t)));
    }
  };

  if (!isChat) {
    return (
      <div className="app">
        <div className="hero">
          <BrandHeader ref={headerRef} compact={false} />
          <WelcomeScreen
            defaultBrand={DEFAULT_BRAND}
            message={message}
            onMessageChange={setMessage}
            onSubmit={handleSubmit}
            loading={false}
            error={null}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="app app--chat">
      <BrandHeader ref={headerRef} compact />

      <div className="conversation">
        {turns.map((turn) => (
          <div key={turn.id} className="turn">
            <UserMessageBubble message={turn.message} />
            {turn.loading && <div className="loading-indicator">Analyzing…</div>}
            {turn.error && (
              <div className="assistant-card assistant-card--error" role="alert">
                {turn.error}
              </div>
            )}
            {turn.result && <AnalysisResult result={turn.result} />}
          </div>
        ))}
      </div>

      <div className="composer-dock">
        <ChatInput
          onSubmit={handleSubmit}
          defaultBrand={DEFAULT_BRAND}
          disabled={turns.some((t) => t.loading)}
          error={null}
          value={message}
          onValueChange={setMessage}
        />
      </div>
    </div>
  );
}
