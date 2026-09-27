import MessageBubble from './MessageBubble.jsx';

/**
 * Out-of-scope or unverifiable question: point the student to a person or
 * resource instead of guessing (QA-02, US-05, US-06).
 */
export default function RedirectMessageRenderer({ message }) {
  const { message: text, resourceName, url } = message.content;

  return (
    <MessageBubble
      from="assistant"
      variant="redirect"
      timestamp={message.timestamp}
    >
      <p>
        {text ??
          "I can't answer that one reliably. Please contact your advisor."}
      </p>
      {url && (
        <a
          className="button button--secondary"
          href={url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {resourceName ?? 'Get help'}
        </a>
      )}
    </MessageBubble>
  );
}
