import MessageBubble from './MessageBubble.jsx';

/** A request that failed before we got an answer. */
export default function ErrorMessageRenderer({ message }) {
  return (
    <MessageBubble
      from="assistant"
      variant="error"
      timestamp={message.timestamp}
    >
      <p>{message.content.message ?? 'Something went wrong.'}</p>
      <p className="bubble__hint">Please try again in a moment.</p>
    </MessageBubble>
  );
}
