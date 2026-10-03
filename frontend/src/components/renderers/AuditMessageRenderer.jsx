import { useState } from 'react';

import FormattedText from './FormattedText.jsx';
import MessageBubble from './MessageBubble.jsx';
import MilestoneChecklist from './MilestoneChecklist.jsx';
import { summarizeAudit } from './auditSummary.js';

// Longer course lists start collapsed so the bubble stays easy to scan.
const COLLAPSED_COURSE_COUNT = 5;

function alternativeNote(content) {
  const courses = content.nextCourses || [];
  if (!content.leadCourseNotOfferedNextTerm || courses.length === 0) {
    return '';
  }
  const codes = courses.map((course) => course.code).filter(Boolean);
  const listed = codes.length <= 1
    ? codes[0]
    : `${codes.slice(0, -1).join(', ')} and ${codes[codes.length - 1]}`;
  const term = content.nextTerm?.name;
  const when = term ? ` in ${term}` : ' next term';
  return `${content.leadCourse?.code} is not offered next term. `
    + `You could take ${listed}${when} instead.`;
}

/** Degree audit result (US-01). */
export default function AuditMessageRenderer({ message }) {
  const { message: text } = message.content;
  const audit = summarizeAudit(message.content);
  const [showAll, setShowAll] = useState(false);
  const hasNumbers = audit.completed != null || audit.remaining != null ||
    audit.missing.length > 0 || audit.met;

  const note = alternativeNote(message.content);
  const hiddenCount = audit.missing.length - COLLAPSED_COURSE_COUNT;
  const visibleCourses = showAll || hiddenCount <= 0
    ? audit.missing
    : audit.missing.slice(0, COLLAPSED_COURSE_COUNT);

  return (
    <MessageBubble from="assistant" timestamp={message.timestamp}>
      {!hasNumbers && text && <FormattedText text={text} />}
      {hasNumbers && <div className="audit">
        <p className="audit__eyebrow">
          Degree audit
          {audit.programName && <> · {audit.programName}</>}
        </p>

        {audit.completed != null && (
          <p className="audit__headline">
            <span className="audit__big">{audit.completed}</span>
            {audit.required != null && <> of {audit.required}</>} credits
            completed
            {audit.percent != null && (
              <span className="audit__percent">{audit.percent}%</span>
            )}
          </p>
        )}

        {audit.percent != null && (
          <div
            className="progress"
            role="progressbar"
            aria-label="Degree progress"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={audit.percent}
          >
            <div
              className={`progress__fill${audit.met ? ' progress__fill--done' : ''}`}
              style={{ width: `${audit.percent}%` }}
            />
          </div>
        )}

        <p className={`audit__status${audit.met ? ' audit__status--done' : ''}`}>
          {audit.met ? (
            '✓ All degree requirements met'
          ) : (
            <>
              {audit.remaining != null && (
                <strong>{audit.remaining} credits remaining</strong>
              )}
              {audit.remaining != null && audit.missing.length > 0 && ' · '}
              {audit.missing.length > 0 && (
                <>
                  {audit.missing.length}{' '}
                  {audit.missing.length === 1 ? 'course' : 'courses'} left
                </>
              )}
            </>
          )}
        </p>
      </div>}

      {audit.missing.length > 0 && (
        <section>
          <h3 className="bubble__heading">Still required</h3>
          <ul className="course-rows">
            {visibleCourses.map((course) => (
              <li key={course.code} className="course-row">
                <span className="course-row__code">{course.code}</span>
                <span className="course-row__title">{course.title}</span>
                {course.credits != null && (
                  <span className="course-row__credits">
                    {course.credits} cr
                  </span>
                )}
              </li>
            ))}
          </ul>
          {hiddenCount > 0 && (
            <button
              type="button"
              className="link-button"
              onClick={() => setShowAll(!showAll)}
            >
              {showAll ? 'Show fewer' : `Show all ${audit.missing.length} courses`}
            </button>
          )}
        </section>
      )}

      {(message.content.milestones || []).length > 0 && (
        <MilestoneChecklist
          milestones={message.content.milestones}
          showPrompt={message.content.offerMilestones}
        />
      )}

      {note && <p>{note}</p>}
      {message.content.needsAdvising && message.content.advisingUrl && (
        <p>
          {message.content.leadCourse?.code} is not offered next term,
          and no other required course is open then. Book an advising
          appointment.
        </p>
      )}
      {message.content.needsAdvising && message.content.advisingUrl && (
        <a
          className="button button--secondary"
          href={message.content.advisingUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          {message.content.advisingResourceName
            ?? 'Book an advising appointment'}
        </a>
      )}

      {hasNumbers && text && (
        <details className="explanation">
          <summary>Show full explanation</summary>
          <FormattedText text={text} />
        </details>
      )}
    </MessageBubble>
  );
}
