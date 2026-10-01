import MessageBubble from './MessageBubble.jsx';
import MilestoneChecklist from './MilestoneChecklist.jsx';

/** Course recommendations (US-03) and next steps outside of class (US-07). */
export default function RecommendationMessageRenderer({ message }) {
  const {
    message: text,
    courses = [],
    milestones = [],
    resourceName,
    url,
    advisingResourceName,
    advisingUrl,
  } = message.content;

  return (
    <MessageBubble from="assistant" timestamp={message.timestamp}>
      {text && <p>{text}</p>}
      {courses.length > 0 && (
        <ul className="courses">
          {courses.map((course) => (
            <li key={course.code} className="course">
              <div className="course__header">
                <span className="course__code">{course.code}</span>
                <span className="course__title">{course.title}</span>
              </div>
              {course.description && (
                <p className="course__description">{course.description}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {milestones.length > 0 && <MilestoneChecklist milestones={milestones} />}
      {url && (
        <a
          className="button button--secondary"
          href={url}
          target="_blank"
          rel="noopener noreferrer"
        >
          {resourceName ?? 'Career Services'}
        </a>
      )}
      {advisingUrl && (
        <a
          className="button button--secondary"
          href={advisingUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          {advisingResourceName ?? 'Talk to advising'}
        </a>
      )}
    </MessageBubble>
  );
}
