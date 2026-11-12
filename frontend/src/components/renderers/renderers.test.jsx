import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { MessageType } from '../../models/message.js';
import ErrorMessageRenderer from './ErrorMessageRenderer.jsx';
import FormattedText, { toBlocks } from './FormattedText.jsx';
import MessageBubble from './MessageBubble.jsx';
import MilestoneChecklist, {
  MILESTONE_PROMPT,
  formatCreditBand,
} from './MilestoneChecklist.jsx';
import QueryMessageRenderer from './QueryMessageRenderer.jsx';
import RedirectMessageRenderer from './RedirectMessageRenderer.jsx';
import SyllabusView from './SyllabusView.jsx';
import { getRenderer } from './index.js';

const timestamp = new Date('2026-11-11T15:30:00Z');

describe('toBlocks', () => {
  it('splits paragraphs and bullet lists', () => {
    const blocks = toBlocks('Take these next.\n\n* MSSE 692\n* MSSE 696\n\nGood luck.');

    expect(blocks).toEqual([
      { kind: 'paragraph', text: 'Take these next.' },
      { kind: 'list', items: ['MSSE 692', 'MSSE 696'] },
      { kind: 'paragraph', text: 'Good luck.' },
    ]);
  });

  it('joins wrapped lines into one paragraph and handles empty input', () => {
    expect(toBlocks('one line\nwrapped')).toEqual([
      { kind: 'paragraph', text: 'one line wrapped' },
    ]);
    expect(toBlocks(undefined)).toEqual([]);
  });
});

describe('FormattedText', () => {
  it('renders bold spans and list items', () => {
    const html = renderToStaticMarkup(
      <FormattedText text={'**Required:** MSSE 692\n\n- first\n- second'} />,
    );

    expect(html).toContain('<strong>Required:</strong>');
    expect(html).toContain('<li>first</li>');
    expect(html).toContain('<li>second</li>');
  });
});

describe('formatCreditBand', () => {
  it('formats closed, open-ended, and unknown bands', () => {
    expect(formatCreditBand(0, 12)).toBe('0–12 credits');
    expect(formatCreditBand(25, null)).toBe('25+ credits');
    expect(formatCreditBand(null, null)).toBe('');
  });
});

describe('MilestoneChecklist', () => {
  const milestones = [{
    label: 'Foundations',
    creditMin: 0,
    creditMax: 12,
    nextActions: ['Review your degree plan'],
  }];

  it('lists each milestone with its next actions', () => {
    const html = renderToStaticMarkup(<MilestoneChecklist milestones={milestones} />);

    expect(html).toContain('Foundations');
    expect(html).toContain('0–12 credits');
    expect(html).toContain('Review your degree plan');
    expect(html).not.toContain(MILESTONE_PROMPT);
  });

  it('shows the prompt when asked', () => {
    const html = renderToStaticMarkup(
      <MilestoneChecklist milestones={milestones} showPrompt />,
    );

    expect(html).toContain(MILESTONE_PROMPT);
  });
});

describe('MessageBubble and message renderers', () => {
  it('wraps content in a bubble for the speaker', () => {
    const html = renderToStaticMarkup(
      <MessageBubble from="assistant" variant="redirect" timestamp={timestamp}>
        <p>hello</p>
      </MessageBubble>,
    );

    expect(html).toContain('bubble--assistant');
    expect(html).toContain('bubble--redirect');
    expect(html).toContain('<p>hello</p>');
    expect(html).toContain('dateTime="2026-11-11T15:30:00.000Z"');
  });

  it('renders the student question', () => {
    const html = renderToStaticMarkup(
      <QueryMessageRenderer message={{ timestamp, content: { text: 'What is next?' } }} />,
    );

    expect(html).toContain('bubble--student');
    expect(html).toContain('What is next?');
  });

  it('shows the error message with a hint', () => {
    const html = renderToStaticMarkup(
      <ErrorMessageRenderer message={{ timestamp, content: { message: 'Down', code: 'INTERNAL_ERROR' } }} />,
    );

    expect(html).toContain('bubble--error');
    expect(html).toContain('Down');
    expect(html).toContain('bubble__hint');
  });

  it('falls back to a generic error line', () => {
    const html = renderToStaticMarkup(
      <ErrorMessageRenderer message={{ timestamp, content: {} }} />,
    );

    expect(html).toContain('Something went wrong.');
  });

  it('links to the resource on a redirect', () => {
    const html = renderToStaticMarkup(
      <RedirectMessageRenderer
        message={{
          timestamp,
          content: {
            message: 'Ask financial aid.',
            url: 'https://example.edu/aid',
            resourceName: 'Financial aid',
          },
        }}
      />,
    );

    expect(html).toContain('Ask financial aid.');
    expect(html).toContain('href="https://example.edu/aid"');
    expect(html).toContain('Financial aid');
  });

  it('uses the error renderer for unknown message types', () => {
    expect(getRenderer(MessageType.QUERY)).toBe(QueryMessageRenderer);
    expect(getRenderer(MessageType.REDIRECT)).toBe(RedirectMessageRenderer);
    expect(getRenderer('not-a-type')).toBe(ErrorMessageRenderer);
  });
});

describe('SyllabusView', () => {
  it('shows the course header, overview and weekly topics', () => {
    const html = renderToStaticMarkup(
      <SyllabusView
        course={{ code: 'MSSE 635', title: 'Software Architecture', credits: 3 }}
        syllabus={{
          overview: 'Architecture styles.',
          objectives: ['Design systems'],
          weeks: [{ week: 1, topic: 'Foundations' }],
        }}
        nextTerm={null}
        summary={null}
      />,
    );

    expect(html).toContain('MSSE 635');
    expect(html).toContain('Software Architecture');
    expect(html).toContain('3 credits');
    expect(html).toContain('Architecture styles.');
    expect(html).toContain('Foundations');
  });
});
