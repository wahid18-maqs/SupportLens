import { SendIcon } from "./Icons";

interface ChatInputProps {
  onSubmit: (message: string, brand: string) => void;
  defaultBrand: string;
  disabled?: boolean;
  error?: string | null;
  value: string;
  onValueChange: (value: string) => void;
}

export default function ChatInput({ onSubmit, defaultBrand, disabled, error, value, onValueChange }: ChatInputProps) {
  const canSubmit = value.trim().length > 0 && !disabled;

  const submit = () => {
    if (!canSubmit) return;
    onSubmit(value.trim(), defaultBrand);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <form className="composer" onSubmit={handleSubmit}>
      <textarea
        className="composer-textarea"
        rows={3}
        placeholder="Paste a customer message here..."
        value={value}
        onChange={(e) => onValueChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-label="Customer message"
      />

      <div className="composer-footer">
        <span className="brand-display">{defaultBrand}</span>

        <button type="submit" className="btn btn-primary composer-send" disabled={!canSubmit}>
          {disabled ? "Analyzing…" : "Analyze"}
          <SendIcon />
        </button>
      </div>

      {error && (
        <p className="composer-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
