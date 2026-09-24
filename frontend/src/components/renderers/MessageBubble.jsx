// Shared chat-bubble frame used by every MessageRenderer.

const timeFormat = new Intl.DateTimeFormat(undefined, {
  hour: 'numeric',
  minute: '2-digit',
});

/**
 * @param {{from: 'student'|'assistant', timestamp: Date,
 *     variant?: string, children: React.ReactNode}} props
 */
export default function MessageBubble({ from, timestamp, variant, children }) {
  const className = ['bubble', `bubble--${from}`, variant && `bubble--${variant}`]
    .filter(Boolean)
    .join(' ');
  return (
    <li className={`message message--${from}`}>
      <div className={className}>{children}</div>
      <time className="message__time" dateTime={timestamp.toISOString()}>
        {timeFormat.format(timestamp)}
      </time>
    </li>
  );
}
