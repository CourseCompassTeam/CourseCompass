import MessageBubble from './MessageBubble.jsx';

/** Course recommendations (US-03). */
export default function RecommendationMessageRenderer({ message }) {
  const { message: text, courses = [] } = message.content;

  return (
    <MessageBubble from="assistant" timestamp={message.timestamp}>
      {text && <p>{text}</p>}
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
    </MessageBubble>
  );
}
