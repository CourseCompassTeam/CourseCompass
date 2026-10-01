import { useState } from 'react';

import MessageBubble from './MessageBubble.jsx';
import { summarizeAudit } from './auditSummary.js';

// Longer course lists start collapsed so the bubble stays easy to scan.
const COLLAPSED_COURSE_COUNT = 5;

/** Degree audit result (US-01). */
export default function AuditMessageRenderer({ message }) {
  const { message: text } = message.content;
  const audit = summarizeAudit(message.content);
  const [showAll, setShowAll] = useState(false);
  const hasNumbers = audit.completed != null || audit.remaining != null ||
    audit.missing.length > 0 || audit.met;

  const hiddenCount = audit.missing.length - COLLAPSED_COURSE_COUNT;
  const visibleCourses = showAll || hiddenCount <= 0
    ? audit.missing
    : audit.missing.slice(0, COLLAPSED_COURSE_COUNT);

  return (
    <MessageBubble from="assistant" timestamp={message.timestamp}>
      {!hasNumbers && text && <p>{text}</p>}
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

      {hasNumbers && text && (
        <details className="explanation">
          <summary>Show full explanation</summary>
          <p>{text}</p>
        </details>
      )}
    </MessageBubble>
  );
}
