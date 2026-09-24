import { useEffect, useRef, useState } from 'react';

import { MessageType, createMessage } from '../models/message.js';
import ChatInput from './ChatInput.jsx';
import { getRenderer } from './renderers/index.js';

const SUGGESTIONS = [
  'What do I still need to graduate?',
  'Recommend a course that fits my interest in project management',
  'Can my transfer credit count toward a requirement?',
];

/**
 * Holds the conversation and hands each message to its renderer.
 * @param {{chatService: import('../services/chatService.js').ChatService}}
 *     props
 */
export default function ChatContainer({ chatService }) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isLoading]);

  async function handleSubmit(query) {
    const append = (message) => setMessages((prev) => [...prev, message]);

    append(createMessage({ type: MessageType.QUERY, content: { text: query } }));
    setIsLoading(true);
    try {
      append(await chatService.sendQuery(query));
    } catch (error) {
      append(createMessage({
        type: MessageType.ERROR,
        content: { message: error.message },
      }));
    } finally {
      setIsLoading(false);
    }
  }

  function renderMessage(message) {
    const Renderer = getRenderer(message.type);
    return <Renderer key={message.id} message={message} />;
  }

  return (
    <section className="chat" aria-label="Chat">
      <div className="chat__scroll">
        {messages.length === 0 ? (
          <div className="chat__empty">
            <h2>How can I help?</h2>
            <p>
              Ask about your degree progress, course details, or what to take
              next.
            </p>
            <ul className="suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <li key={suggestion}>
                  <button
                    type="button"
                    className="suggestion"
                    onClick={() => handleSubmit(suggestion)}
                    disabled={isLoading}
                  >
                    {suggestion}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <ol className="messages" aria-live="polite">
            {messages.map(renderMessage)}
            {isLoading && (
              <li className="message message--assistant">
                <div className="bubble bubble--assistant typing" role="status">
                  <span className="visually-hidden">Thinking…</span>
                  <span className="typing__dot" />
                  <span className="typing__dot" />
                  <span className="typing__dot" />
                </div>
              </li>
            )}
          </ol>
        )}
        <div ref={endRef} />
      </div>
      <ChatInput onSubmit={handleSubmit} disabled={isLoading} />
    </section>
  );
}
