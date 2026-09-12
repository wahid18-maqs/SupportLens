import ChatInput from "./ChatInput";
import ExampleButtons from "./ExampleButtons";

interface WelcomeScreenProps {
  defaultBrand: string;
  message: string;
  onMessageChange: (value: string) => void;
  onSubmit: (message: string, brand: string) => void;
  loading: boolean;
  error: string | null;
}

export default function WelcomeScreen({
  defaultBrand,
  message,
  onMessageChange,
  onSubmit,
  loading,
  error,
}: WelcomeScreenProps) {
  return (
    <div className="welcome">
      <h1 className="welcome-heading">How can I help with this support message?</h1>
      <p className="welcome-description">
        Paste in a customer message and SupportLens will classify its intent, draft a reply grounded in similar past
        conversations, and recommend whether it's safe to auto-handle or should go to a human.
      </p>

      <ChatInput
        onSubmit={onSubmit}
        defaultBrand={defaultBrand}
        disabled={loading}
        error={error}
        value={message}
        onValueChange={onMessageChange}
      />

      <ExampleButtons onSelect={onMessageChange} disabled={loading} />
    </div>
  );
}
