// Syllabus answer for one course: header, next-term status, prerequisites,
// overview, numbered weekly topics, and objectives. Facts come from the
// course data and stored syllabus; the AI's summary sits collapsed below.

import FormattedText from './FormattedText.jsx';

/**
 * @param {{course: object, syllabus: {overview: string,
 *     objectives: string[], weeks: Array<{week: number, topic: string}>},
 *     nextTerm: ?{name: string}, summary: ?string}} props
 */
export default function SyllabusView({ course, syllabus, nextTerm, summary }) {
  const prerequisites = course.prerequisites ?? [];
  const offeredTerms = course.offeredTerms ?? [];

  return (
    <div className="syllabus">
      <header className="syllabus__header">
        <p className="audit__eyebrow">
          Syllabus{course.credits != null && <> · {course.credits} credits</>}
        </p>
        <h3 className="syllabus__title">
          <span className="course__code">{course.code}</span>{' '}
          {course.title}
        </h3>
        {nextTerm?.name && course.offeredNextTerm != null && (
          <p
            className={`syllabus__offering${
              course.offeredNextTerm ? ' syllabus__offering--yes' : ''}`}
          >
            {course.offeredNextTerm
              ? `✓ Offered next term (${nextTerm.name})`
              : `Not offered next term (${nextTerm.name})`}
          </p>
        )}
        {offeredTerms.length > 0 && (
          <p className="syllabus__meta">Offered: {offeredTerms.join(' · ')}</p>
        )}
      </header>

      {prerequisites.length > 0 && (
        <section>
          <h4 className="bubble__heading">Prerequisites</h4>
          <ul className="tags">
            {prerequisites.map((code) => (
              <li key={code} className="tag">{code}</li>
            ))}
          </ul>
        </section>
      )}

      {syllabus.overview && <p>{syllabus.overview}</p>}

      <section>
        <h4 className="bubble__heading">Weekly topics</h4>
        <ol className="weeks">
          {syllabus.weeks.map(({ week, topic }) => (
            <li key={week} className="week">
              <span className="week__number">Week {week}</span>
              <span>{topic}</span>
            </li>
          ))}
        </ol>
      </section>

      {syllabus.objectives.length > 0 && (
        <section>
          <h4 className="bubble__heading">Course objectives</h4>
          <ul className="objectives">
            {syllabus.objectives.map((objective) => (
              <li key={objective}>{objective}</li>
            ))}
          </ul>
        </section>
      )}

      {summary && (
        <details className="explanation">
          <summary>Show AI summary</summary>
          <FormattedText text={summary} />
        </details>
      )}
    </div>
  );
}
