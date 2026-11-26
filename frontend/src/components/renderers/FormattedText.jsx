// Shows an AI reply with its paragraphs and bullet lists intact, instead of
// one block of text with stray "*" characters. Builds React elements only
// (never raw HTML), so reply text can't inject markup.

const BULLET = /^\s*(?:[*•-])\s+/;
// "1. Item" or "1) Item".
const NUMBERED = /^\s*(\d+)[.)]\s+/;

/**
 * Splits text into paragraph and list blocks.
 * @param {string} text The reply text.
 * @returns {Array<{kind: 'paragraph', text: string} |
 *     {kind: 'list', ordered: boolean, start?: number, items: string[]}>}
 *     start is the first number of an ordered list.
 */
export function toBlocks(text) {
  const blocks = [];
  for (const chunk of String(text ?? '').split(/\n\s*\n/)) {
    let paragraph = [];
    let list = null;
    const flushParagraph = () => {
      if (paragraph.length) {
        blocks.push({ kind: 'paragraph', text: paragraph.join(' ') });
        paragraph = [];
      }
    };
    for (const rawLine of chunk.split('\n')) {
      const line = rawLine.trim();
      if (!line) {
        continue;
      }
      const number = NUMBERED.exec(line);
      if (number || BULLET.test(line)) {
        flushParagraph();
        const ordered = Boolean(number);
        if (!list || list.ordered !== ordered) {
          list = ordered
            ? { kind: 'list', ordered, start: Number(number[1]), items: [] }
            : { kind: 'list', ordered, items: [] };
          blocks.push(list);
        }
        list.items.push(line.replace(ordered ? NUMBERED : BULLET, ''));
      } else {
        list = null;
        paragraph.push(line);
      }
    }
    flushParagraph();
  }
  return blocks;
}

/** Renders **bold** spans; everything else is plain text. */
function Inline({ text }) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4
      ? <strong key={index}>{part.slice(2, -2)}</strong>
      : part,
  );
}

/** @param {{text: string}} props */
export default function FormattedText({ text }) {
  return (
    <div className="formatted-text">
      {toBlocks(text).map((block, index) => {
        if (block.kind !== 'list') {
          return <p key={index}><Inline text={block.text} /></p>;
        }
        const items = block.items.map((item, itemIndex) => (
          <li key={itemIndex}><Inline text={item} /></li>
        ));
        return block.ordered ? (
          <ol key={index} start={block.start === 1 ? undefined : block.start}>
            {items}
          </ol>
        ) : (
          <ul key={index}>{items}</ul>
        );
      })}
    </div>
  );
}
