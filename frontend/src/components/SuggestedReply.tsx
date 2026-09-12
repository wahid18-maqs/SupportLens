import CopyReplyButton from "./CopyReplyButton";
import { linkify } from "../utils/text";


export default function SuggestedReply({ reply }: { reply: string }) {
  return (
    <div className="subsection">
      <span className="stat-label">Suggested reply</span>
      <p className="reply-text">{linkify(reply)}</p>
      <CopyReplyButton text={reply} />
    </div>
  );
}
