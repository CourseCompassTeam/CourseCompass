import FormattedText from './FormattedText.jsx';
import MessageBubble from './MessageBubble.jsx';
import MilestoneChecklist from './MilestoneChecklist.jsx';
import SyllabusView from './SyllabusView.jsx';
import { parseSyllabus } from './syllabus.js';

/** Course recommendations (US-03) and next steps outside of class (US-07). */
export default function RecommendationMessageRenderer({ message }) {
  const {
    message: text,
    courses = [],
    milestones = [],
    offerMilestones = false,
    resourceName,
    url,
    advisingResourceName,
    advisingUrl,
    summarizeSyllabus = false,
    nextTerm,
  } = message.content;

  // A syllabus question about one course gets the syllabus layout, built
  // from the stored syllabus. Anything else falls back to the course list.
  const syllabus = summarizeSyllabus && courses.length === 1
    ? parseSyllabus(courses[0].syllabusText)
    : null;

  return (
    <MessageBubble from="assistant" timestamp={message.timestamp}>
      {syllabus ? (
        <SyllabusView
          course={courses[0]}
          syllabus={syllabus}
          nextTerm={nextTerm}
          summary={text}
        />
      ) : (
        text && <FormattedText text={text} />
      )}
      {!syllabus && courses.length > 0 && (
        <ul className="courses">
          {courses.map((course) => (
            <li key={course.code} className="course">
              <div className="course__header">
                <span className="course__code">{course.code}</span>
                <span className="course__title">{course.title}</span>
              </div>
              {course.programs?.length > 0 && (
                <p className="course__description">
                  {course.programs.join(', ')}
                </p>
              )}
              {course.description && (
                <p className="course__description">{course.description}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {milestones.length > 0 && (
        <MilestoneChecklist
          milestones={milestones}
          showPrompt={offerMilestones}
        />
      )}
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
