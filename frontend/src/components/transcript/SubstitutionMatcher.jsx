import { useState } from 'react';

// Drag-and-drop matcher: drop a transcript course on a requirement it
// substitutes for (one course per requirement), or drop it in the
// "Cannot apply" bin. Presentational only; the parent owns the data.

const POOL = 'pool';
const BIN = 'bin';

/**
 * @param {{
 *   requirements: Array<{code: string, title: string, credits: number}>,
 *   courses: Array<{code: string, title: string, credits: number}>,
 *   initialAssignments?: Record<string, string>,
 *   onSave?: (assignments: Record<string, string>) => void,
 * }} props
 * `courses` are the transcript courses not directly applied to a requirement.
 * `initialAssignments` maps requirement code to course code.
 */
export default function SubstitutionMatcher({
  requirements,
  courses,
  initialAssignments = {},
  onSave,
}) {
  const [assignments, setAssignments] = useState(initialAssignments);
  const [binned, setBinned] = useState([]);
  const [dragging, setDragging] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);

  const courseByCode = new Map(courses.map((course) => [course.code, course]));
  const assignedCodes = new Set(Object.values(assignments));
  const poolCourses = courses.filter(
    (course) => !assignedCodes.has(course.code) && !binned.includes(course.code),
  );
  const binCourses = courses.filter((course) => binned.includes(course.code));

  // Moves a course to a target, removing it from wherever it was.
  function move(courseCode, target) {
    setBinned((current) => current.filter((code) => code !== courseCode));
    setAssignments((current) => {
      const next = { ...current };
      for (const [req, code] of Object.entries(next)) {
        if (code === courseCode) delete next[req];
      }
      if (target !== POOL && target !== BIN) next[target] = courseCode;
      return next;
    });
    if (target === BIN) setBinned((current) => [...current, courseCode]);
  }

  function dropProps(target) {
    return {
      onDragOver: (event) => {
        event.preventDefault();
        setDropTarget(target);
      },
      onDragLeave: () => setDropTarget(null),
      onDrop: (event) => {
        event.preventDefault();
        const courseCode = event.dataTransfer.getData('text/plain') || dragging;
        setDropTarget(null);
        setDragging(null);
        if (courseCode) move(courseCode, target);
      },
    };
  }

  function chip(course) {
    return (
      <li
        key={course.code}
        className="match-chip"
        draggable
        onDragStart={(event) => {
          event.dataTransfer.setData('text/plain', course.code);
          event.dataTransfer.effectAllowed = 'move';
          setDragging(course.code);
        }}
        onDragEnd={() => {
          setDragging(null);
          setDropTarget(null);
        }}
      >
        <span className="match-chip__code">{course.code}</span>
        <span className="match-chip__title">{course.title}</span>
        <span className="match-chip__note">{course.credits} cr</span>
      </li>
    );
  }

  const overClass = (target) =>
    dropTarget === target ? ' match-drop--over' : '';

  return (
    <section className="match" aria-label="Match transcript courses">
      <p className="match__disclaimer">
        Substitutions you declare here are your own. Verify any substitution
        with your advisor before relying on it for graduation.
      </p>

      <div className="match__grid">
        <div>
          <h3 className="match__heading">Requirements</h3>
          <ul className="match__slots">
            {requirements.map((req) => {
              const placed = courseByCode.get(assignments[req.code]);
              return (
                <li
                  key={req.code}
                  className={`match-slot${overClass(req.code)}`}
                  aria-label={`${req.code} ${req.title}`}
                  {...dropProps(req.code)}
                >
                  <div className="match-slot__req">
                    <span className="match-chip__code">{req.code}</span>
                    <span className="match-chip__title">{req.title}</span>
                    <span className="match-chip__note">{req.credits} cr</span>
                  </div>
                  {placed ? (
                    <ul className="match-slot__filled">{chip(placed)}</ul>
                  ) : (
                    <p className="match-slot__empty">Drop a course here</p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>

        <div>
          <h3 className="match__heading">Your transcript courses</h3>
          <ul className={`match__pool${overClass(POOL)}`} {...dropProps(POOL)}>
            {poolCourses.length === 0 ? (
              <li className="match-slot__empty">Every course is placed.</li>
            ) : (
              poolCourses.map(chip)
            )}
          </ul>

          <h3 className="match__heading">Cannot apply</h3>
          <ul className={`match__bin${overClass(BIN)}`} {...dropProps(BIN)}>
            {binCourses.length === 0 ? (
              <li className="match-slot__empty">
                Courses that do not fill any requirement go here.
              </li>
            ) : (
              binCourses.map(chip)
            )}
          </ul>        </div>
      </div>

      <div className="match__actions">
        <button
          type="button"
          className="button button--secondary"
          onClick={() => {
            setAssignments(initialAssignments);
            setBinned([]);
          }}
        >
          Reset
        </button>
        <button
          type="button"
          className="button"
          onClick={() => onSave?.(assignments)}
        >
          Save substitutions
        </button>
      </div>
    </section>
  );
}
