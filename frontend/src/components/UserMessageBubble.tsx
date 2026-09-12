export default function UserMessageBubble({ message }: { message: string }) {
  return (
    <div className="user-message-row">
      <div className="user-message-bubble">{message}</div>
    </div>
  );
}
