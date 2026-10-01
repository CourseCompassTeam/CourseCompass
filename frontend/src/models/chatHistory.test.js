import { describe, expect, it } from 'vitest';

import {
  MAX_HISTORY_TEXT_LENGTH,
  buildHistory,
  nextQuestionNumber,
} from './chatHistory.js';
import { MessageType } from './message.js';

const question = (text) => ({ type: MessageType.QUERY, content: { text } });
const answer = (message, type = MessageType.AUDIT) => ({
  type,
  content: { message },
});
const error = () => ({ type: MessageType.ERROR, content: { message: 'x' } });

describe('nextQuestionNumber', () => {
  it('counts every student question still on screen', () => {
    expect(nextQuestionNumber([])).toBe(1);
    expect(nextQuestionNumber([
      question('q1'),
      answer('a1'),
      question('q2'),
      answer('a2'),
      question('q3'),
      answer('a3'),
    ])).toBe(4);
  });
});

describe('buildHistory', () => {
  it('returns an empty history for a new conversation', () => {
    expect(buildHistory([])).toEqual([]);
  });

  it('pairs questions with answers, oldest first', () => {
    const history = buildHistory([
      question('What is MSSE 635?'),
      answer(
        'MSSE 635 is Software Architecture and Design.',
        MessageType.RECOMMENDATION,
      ),
      question('What do I need first?'),
      answer('You need MSSE 610 first.', MessageType.REDIRECT),
    ]);

    expect(history).toEqual([
      { role: 'student', text: 'What is MSSE 635?' },
      {
        role: 'assistant',
        text: 'MSSE 635 is Software Architecture and Design.',
      },
      { role: 'student', text: 'What do I need first?' },
      { role: 'assistant', text: 'You need MSSE 610 first.' },
    ]);
  });

  it('keeps only the last 3 exchanges', () => {
    const messages = [1, 2, 3, 4].flatMap((n) => [
      question(`q${n}`),
      answer(`a${n}`),
    ]);

    const history = buildHistory(messages);

    expect(history).toHaveLength(6);
    expect(history[0]).toEqual({ role: 'student', text: 'q2' });
    expect(history[5]).toEqual({ role: 'assistant', text: 'a4' });
  });

  it('drops questions that ended in an error', () => {
    const history = buildHistory([
      question('q1'),
      error(),
      question('q2'),
      answer('a2'),
    ]);

    expect(history).toEqual([
      { role: 'student', text: 'q2' },
      { role: 'assistant', text: 'a2' },
    ]);
  });

  it('skips answers without text', () => {
    const history = buildHistory([question('q1'), answer(undefined)]);
    expect(history).toEqual([]);
  });

  it('shortens very long messages', () => {
    const long = 'x'.repeat(MAX_HISTORY_TEXT_LENGTH + 50);
    const history = buildHistory([question('q1'), answer(long)]);
    expect(history[1].text).toHaveLength(MAX_HISTORY_TEXT_LENGTH);
  });
});
