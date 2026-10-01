import MessageBubble from './MessageBubble.jsx';
import { getErrorHint } from './errorHints.js';

/** A request that failed before we got an answer. */
export default function ErrorMessageRenderer({ message }) {
  const { message: text, code } = message.content;
  return (
    <MessageBubble
      from="assistant"
      variant="error"
      timestamp={message.timestamp}
    >
      <p>{text ?? 'Something went wrong.'}</p>
      <p className="bubble__hint">{getErrorHint(code)}</p>
    </MessageBubble>
  );
}
