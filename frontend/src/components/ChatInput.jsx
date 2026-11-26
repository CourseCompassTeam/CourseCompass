import { useState } from 'react';

// Longest question a student can type in one message.
export const MAX_QUERY_LENGTH = 500;

// The counter is highlighted once this few characters are left.
const LOW_REMAINING = 50;

/**
 * Text box for the student's question. Enter sends, Shift+Enter adds a
 * new line. Questions are capped at MAX_QUERY_LENGTH characters, with a
 * counter under the box.
 * @param {{onSubmit: (query: string) => void, disabled: boolean}} props
 */
export default function ChatInput({ onSubmit, disabled }) {
  const [text, setText] = useState('');
  const canSend = !disabled && text.trim().length > 0;
  const remaining = MAX_QUERY_LENGTH - text.length;

  function submit() {
    if (!canSend) {
      return;
    }
    onSubmit(text.trim());
    setText('');
  }

  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      className="chat-input"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label htmlFor="chat-input-text" className="visually-hidden">
        Ask a question
      </label>
      <textarea
        id="chat-input-text"
        className="chat-input__text"
        rows={1}
        placeholder="Ask a question…"
        maxLength={MAX_QUERY_LENGTH}
        aria-describedby="chat-input-count"
        value={text}
        onChange={(event) => setText(event.target.value.slice(0, MAX_QUERY_LENGTH))}
        onKeyDown={handleKeyDown}
      />
      <button type="submit" className="button" disabled={!canSend}>
        Send
      </button>
      <p
        id="chat-input-count"
        className={
          remaining <= LOW_REMAINING
            ? 'chat-input__count chat-input__count--low'
            : 'chat-input__count'
        }
      >
        {`${text.length}/${MAX_QUERY_LENGTH}`}
      </p>
    </form>
  );
}
