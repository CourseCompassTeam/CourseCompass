import { useEffect, useId, useRef, useState } from 'react';

import {
  DEFAULT_COURSES_PER_TERM,
  MAX_COURSES_PER_TERM,
} from '../../services/scheduleService.js';
import { courseCountLabel } from '../transcript/transcriptText.js';
import {
  CALENDAR_FILE_NAME,
  buildScheduleCalendar,
  hasCalendarDates,
} from './scheduleCalendar.js';
import {
  creditLabel,
  formatTermDates,
  getScheduleErrorHint,
  totalCredits,
} from './scheduleText.js';

const PER_TERM_OPTIONS = Array.from(
  { length: MAX_COURSES_PER_TERM },
  (_, index) => index + 1,
);

/**
 * Header button that opens the schedule dialog.
 * @param {{scheduleService:
 *     import('../../services/scheduleService.js').ScheduleService}} props
 */
export function ScheduleButton({ scheduleService }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        className="button button--secondary"
        onClick={() => setIsOpen(true)}
        aria-label="Schedule"
      >
        Schedule
      </button>
      <ScheduleDialog
        scheduleService={scheduleService}
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </>
  );
}

/**
 * Modal for building the student's schedule, reviewing it term by term,
 * and exporting it as a calendar file. Schedules aren't saved. The last
 * one built stays here until the page reloads, since the dialog stays
 * mounted between opens.
 *
 * @param {{
 *   scheduleService:
 *       import('../../services/scheduleService.js').ScheduleService,
 *   isOpen: boolean,
 *   onClose: () => void,
 * }} props
 */
export default function ScheduleDialog({ scheduleService, isOpen, onClose }) {
  const dialogRef = useRef(null);
  const titleId = useId();
  const perTermId = useId();

  const [schedule, setSchedule] = useState(null);
  const [coursesPerTerm, setCoursesPerTerm] = useState(
    DEFAULT_COURSES_PER_TERM,
  );
  const [isBuilding, setIsBuilding] = useState(false);
  // From the last build: {unplaced, message}.
  const [buildResult, setBuildResult] = useState(null);
  const [exportNotice, setExportNotice] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen && !dialog.open) {
      dialog.showModal();
      setExportNotice(null);
      setError(null);
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  async function build(event) {
    event.preventDefault();
    if (isBuilding) return;
    setError(null);
    setExportNotice(null);
    setIsBuilding(true);
    try {
      const result = await scheduleService.buildSchedule({ coursesPerTerm });
      setBuildResult({ unplaced: result.unplaced, message: result.message });
      // When nothing could be placed, keep showing the last schedule.
      if (result.schedule) {
        setSchedule(result.schedule);
      }
    } catch (buildError) {
      setError(buildError);
    } finally {
      setIsBuilding(false);
    }
  }

  function exportToCalendar() {
    const { ics, skippedTerms } = buildScheduleCalendar(schedule);
    if (!ics) return;
    downloadFile(CALENDAR_FILE_NAME, ics);
    setExportNotice({ skippedTerms });
  }

  return (
    <dialog
      ref={dialogRef}
      className="dialog dialog--wide"
      aria-labelledby={titleId}
      onClose={onClose}
      onCancel={(event) => {
        if (isBuilding) event.preventDefault();
      }}
    >
      <div className="dialog__header">
        <h2 id={titleId} className="dialog__title">Your schedule</h2>
        <button
          type="button"
          className="dialog__close"
          onClick={onClose}
          disabled={isBuilding}
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div className="dialog__body">
        <p>
          CourseCompass plans your remaining required courses term by term.
          Each course comes after its prerequisites, in a term when it's
          offered. Courses that satisfy the most prerequisites come first.
        </p>

        <form className="schedule-build" onSubmit={build}>
          <label htmlFor={perTermId} className="schedule-build__label">
            Courses per term
          </label>
          <select
            id={perTermId}
            className="schedule-build__select"
            value={coursesPerTerm}
            disabled={isBuilding}
            onChange={(event) => setCoursesPerTerm(Number(event.target.value))}
          >
            {PER_TERM_OPTIONS.map((count) => (
              <option key={count} value={count}>{count}</option>
            ))}
          </select>
          <button
            type="submit"
            className="button"
            disabled={isBuilding}
          >
            {isBuilding
              ? 'Building…'
              : schedule ? 'Rebuild schedule' : 'Build schedule'}
          </button>
        </form>

        {error && (
          <div className="callout callout--error" role="alert">
            <p>{error.message}</p>
            <p className="bubble__hint">{getScheduleErrorHint(error.code)}</p>
          </div>
        )}

        {buildResult?.message && (
          <div className="callout callout--warning" role="status">
            <p>{buildResult.message}</p>
            {schedule && <p>Your previous schedule is shown below.</p>}
          </div>
        )}

        {!schedule && !buildResult && (
          <p className="schedule-empty">
            Build a schedule to see your remaining required courses planned
            term by term.
          </p>
        )}

        {schedule && (
          <ScheduleView
            schedule={schedule}
            disabled={isBuilding}
            exportNotice={exportNotice}
            onExport={exportToCalendar}
          />
        )}

        {buildResult?.unplaced.length > 0 && (
          <UnplacedCourses courses={buildResult.unplaced} />
        )}

        <div className="dialog__actions">
          <button
            type="button"
            className="button button--secondary"
            onClick={onClose}
            disabled={isBuilding}
          >
            Close
          </button>
        </div>
      </div>
    </dialog>
  );
}

/** The schedule's terms, and the calendar export. */
function ScheduleView({
  schedule,
  disabled,
  exportNotice,
  onExport,
}) {
  const courseCount = schedule.terms.reduce(
    (sum, term) => sum + term.items.length, 0,
  );
  const credits = totalCredits(schedule.terms.flatMap((term) => term.items));
  const canExport = hasCalendarDates(schedule);

  return (
    <section className="schedule" aria-label="Planned schedule">
      <p className="schedule__summary">
        {courseCountLabel(courseCount)} over {schedule.terms.length}{' '}
        {schedule.terms.length === 1 ? 'term' : 'terms'},{' '}
        {creditLabel(credits)}
      </p>

      <ol className="schedule__terms">
        {schedule.terms.map((term) => (
          <li key={term.termName} className="term">
            <div className="term__header">
              <h3 className="term__name">{term.termName}</h3>
              <span className="bubble__hint">
                {[formatTermDates(term.startDate, term.endDate),
                  creditLabel(totalCredits(term.items))]
                  .filter(Boolean)
                  .join(' · ')}
              </span>
            </div>
            <ul className="course-rows">
              {term.items.map((item) => (
                <li key={item.courseId || item.code} className="course-row">
                  <span className="course-row__code">{item.code}</span>
                  <span>{item.title}</span>
                  <span className="course-row__credits">
                    {creditLabel(item.credits)}
                  </span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>

      <div className="schedule__export">
        {canExport ? (
          <p className="bubble__hint">
            This schedule isn't saved, so export it to keep a copy. You'll
            get a calendar file with each course as an all-day event for its
            term, which you can import into Google Calendar, Outlook, or
            Apple Calendar.
          </p>
        ) : (
          <p className="bubble__hint">
            This schedule isn't saved. Calendar export needs the start and
            end dates for each term, and those aren't available yet.
          </p>
        )}
        <button
          type="button"
          className="button"
          onClick={onExport}
          disabled={!canExport || disabled}
        >
          Export to calendar
        </button>
      </div>

      {exportNotice && (
        <div className="callout callout--info" role="status">
          <p>
            Downloaded {CALENDAR_FILE_NAME}. Open it, or import it into your
            calendar app.
          </p>
          {exportNotice.skippedTerms.length > 0 && (
            <p>
              Left out because their dates aren't available:{' '}
              {exportNotice.skippedTerms.join(', ')}.
            </p>
          )}
        </div>
      )}

      <p className="bubble__hint">
        Course offerings can change. Review this plan with your advisor
        before you register.
      </p>
    </section>
  );
}

/** Courses the last build couldn't place, with the reason for each. */
function UnplacedCourses({ courses }) {
  return (
    <section aria-label="Courses not scheduled">
      <h3 className="bubble__heading">
        Couldn't schedule {courseCountLabel(courses.length)}
      </h3>
      <ul className="course-rows">
        {courses.map((course) => (
          <li
            key={course.courseId || course.code}
            className="course-row course-row--two"
          >
            <span className="course-row__code">{course.code}</span>
            <span>
              {course.title}
              <span className="unplaced__reason">{course.reason}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="bubble__hint upload-result__note">
        Ask your advisor how to fit these courses into your plan.
      </p>
    </section>
  );
}

/** Saves text as a file through a temporary download link. */
function downloadFile(fileName, text) {
  const blob = new Blob([text], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.append(link);
  link.click();
  link.remove();
  // Revoke after the click has started the download.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
