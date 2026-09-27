import MessageBubble from './MessageBubble.jsx';

/** The student's own question. */
export default function QueryMessageRenderer({ message }) {
  return (
    <MessageBubble from="student" timestamp={message.timestamp}>
      <p>{message.content.text}</p>
    </MessageBubble>
  );
}
