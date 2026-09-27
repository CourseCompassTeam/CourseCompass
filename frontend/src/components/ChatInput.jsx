import { useState } from 'react';

/**
 * Text box for the student's question. Enter sends, Shift+Enter adds a
 * new line.
 * @param {{onSubmit: (query: string) => void, disabled: boolean}} props
 */
export default function ChatInput({ onSubmit, disabled }) {
  const [text, setText] = useState('');
  const canSend = !disabled && text.trim().length > 0;

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
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button type="submit" className="button" disabled={!canSend}>
        Send
      </button>
    </form>
  );
}
