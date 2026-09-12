import { useState } from "react";
import { CopyIcon } from "./Icons";

/** Copies the suggested reply to the clipboard, with brief "Copied" feedback. */
export default function CopyReplyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      
    }
  };

  return (
    <button type="button" className="btn btn-secondary btn-small copy-btn" onClick={handleCopy}>
      <CopyIcon />
      {copied ? "Copied!" : "Copy reply"}
    </button>
  );
}
