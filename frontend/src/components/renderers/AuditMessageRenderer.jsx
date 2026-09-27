import MessageBubble from './MessageBubble.jsx';

/** Degree audit result (US-01). */
export default function AuditMessageRenderer({ message }) {
  const {
    message: text,
    creditsRemaining,
    requirementsMet,
    missingCourses = [],
  } = message.content;

  return (
    <MessageBubble from="assistant" timestamp={message.timestamp}>
      {text && <p>{text}</p>}
      <dl className="audit">
        <div className="audit__stat">
          <dt>Credits remaining</dt>
          <dd>{creditsRemaining ?? '—'}</dd>
        </div>
        <div className="audit__stat">
          <dt>Status</dt>
          <dd className={requirementsMet ? 'status--done' : 'status--open'}>
            {requirementsMet ? 'All requirements met' : 'In progress'}
          </dd>
        </div>
      </dl>
      {missingCourses.length > 0 && (
        <>
          <h3 className="bubble__heading">Remaining courses</h3>
          <ul className="chips">
            {missingCourses.map((course) => (
              <li key={course} className="chip">{course}</li>
            ))}
          </ul>
        </>
      )}
    </MessageBubble>
  );
}
