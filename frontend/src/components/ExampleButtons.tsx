const EXAMPLES: { label: string; message: string }[] = [
  { label: "Missing package", message: "My package says delivered but I never received it. Where is it?" },
  { label: "Delivery delay", message: "My order hasn't arrived yet and it's already 3 days late." },
  { label: "Refund request", message: "I want a refund for this item, it wasn't what I ordered." },
  { label: "Payment issue", message: "My payment was declined but I was still charged for the order." },
];

interface ExampleButtonsProps {
  onSelect: (message: string) => void;
  disabled?: boolean;
}

/** Quick-fill buttons that populate the composer with a representative example message. */
export default function ExampleButtons({ onSelect, disabled }: ExampleButtonsProps) {
  return (
    <div className="example-buttons">
      {EXAMPLES.map((example) => (
        <button
          key={example.label}
          type="button"
          className="example-btn"
          onClick={() => onSelect(example.message)}
          disabled={disabled}
        >
          {example.label}
        </button>
      ))}
    </div>
  );
}
