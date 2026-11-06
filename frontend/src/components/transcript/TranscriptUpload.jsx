import { createContext, useContext, useId, useRef, useState } from 'react';

import SubstitutionDialog from './SubstitutionDialog.jsx';
import {
  courseCountLabel,
  formatCourseStatus,
  getUploadErrorHint,
} from './transcriptText.js';

// Opens the upload dialog. Null outside a TranscriptUploadProvider.
const OpenUploadContext = createContext(null);
// Opens the substitution matcher. Null outside a TranscriptUploadProvider.
const OpenMatcherContext = createContext(null);

/**
 * Returns a function that opens the transcript upload dialog, or null when
 * no provider is mounted (so callers can hide their upload buttons).
 */
export function useOpenTranscriptUpload() {
  return useContext(OpenUploadContext);
}

/**
 * Returns a function that opens the substitution matcher, or null when no
 * provider is mounted.
 */
export function useOpenSubstitutionMatcher() {
  return useContext(OpenMatcherContext);
}

/** Header button that opens the transcript upload dialog. */
export function TranscriptUploadButton() {
  const open = useOpenTranscriptUpload();
  return (
    <button
      type="button"
      className="button button--secondary"
      onClick={open}
      aria-label="Upload transcript"
    >
      Upload<span className="hide-narrow">&nbsp;transcript</span>
    </button>
  );
}

/**
 * Owns the dialog for uploading a transcript PDF and lets any child open it.
 * The upload replaces every course the student has stored.
 * @param {{transcriptService:
 *     import('../../services/transcriptService.js').TranscriptService,
 *     children: React.ReactNode}} props
 */
export default function TranscriptUploadProvider({
  transcriptService,
  children,
}) {
  const dialogRef = useRef(null);
  const inputRef = useRef(null);
  const titleId = useId();
  const inputId = useId();

  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [matcherOpen, setMatcherOpen] = useState(false);

  function open() {
    reset();
    dialogRef.current?.showModal();
  }

  // The matcher opens on top of the upload dialog's result, so close it.
  function openMatcher() {
    if (!isUploading) {
      dialogRef.current?.close();
    }
    setMatcherOpen(true);
  }

  function close() {
    if (!isUploading) {
      dialogRef.current?.close();
    }
  }

  function reset() {
    setFile(null);
    setResult(null);
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file || isUploading) {
      return;
    }
    setError(null);
    setIsUploading(true);
    try {
      setResult(await transcriptService.uploadTranscript(file));
    } catch (uploadError) {
      setError(uploadError);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <OpenUploadContext.Provider value={open}>
      <OpenMatcherContext.Provider value={openMatcher}>
      {children}
      <SubstitutionDialog
        transcriptService={transcriptService}
        isOpen={matcherOpen}
        onClose={() => setMatcherOpen(false)}
      />
      <dialog
        ref={dialogRef}
        className="dialog"
        aria-labelledby={titleId}
        onCancel={(event) => {
          // Escape can't close the dialog mid-upload.
          if (isUploading) {
            event.preventDefault();
          }
        }}
      >
        <div className="dialog__header">
          <h2 id={titleId} className="dialog__title">Upload transcript</h2>
          <button
            type="button"
            className="dialog__close"
            onClick={close}
            disabled={isUploading}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {result ? (
          <UploadResult
            result={result}
            onDone={close}
            onAgain={reset}
            onMatch={openMatcher}
          />
        ) : (
          <form className="dialog__body" onSubmit={handleSubmit}>
            <p>
              Upload your transcript as a PDF so CourseCompass can answer
              questions about your progress.
            </p>
            <div className="callout callout--warning" role="note">
              <p className="callout__title">This replaces your stored courses.</p>
              <p>
                All course data that CourseCompass has on file for you will
                be overwritten with what's on the provided transcript.
              </p>
            </div>

            <label htmlFor={inputId} className="file-picker">
              <span className="file-picker__label">Transcript PDF</span>
              <input
                ref={inputRef}
                id={inputId}
                type="file"
                accept=".pdf,application/pdf"
                className="file-picker__input"
                disabled={isUploading}
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setError(null);
                }}
              />
            </label>

            {error && (
              <div className="callout callout--error" role="alert">
                <p>{error.message}</p>
                <p className="bubble__hint">{getUploadErrorHint(error.code)}</p>
              </div>
            )}

            <div className="dialog__actions">
              <button
                type="button"
                className="button button--secondary"
                onClick={close}
                disabled={isUploading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="button"
                disabled={!file || isUploading}
              >
                {isUploading ? 'Uploading…' : 'Upload and replace'}
              </button>
            </div>
          </form>
        )}
      </dialog>
      </OpenMatcherContext.Provider>
    </OpenUploadContext.Provider>
  );
}

/** What was saved and skipped after a successful upload. */
function UploadResult({ result, onDone, onAgain, onMatch }) {
  const { saved, skipped, clearedSubstitutions = [] } = result;
  return (
    <div className="dialog__body" role="status">
      <p className="upload-result__headline">
        <span className="upload-result__check" aria-hidden="true">✓</span>
        Transcript updated
      </p>
      <dl className="upload-counts">
        <div className="upload-counts__item">
          <dt>Saved</dt>
          <dd>{saved.length}</dd>
        </div>
        <div className="upload-counts__item">
          <dt>Skipped</dt>
          <dd>{skipped.length}</dd>
        </div>
      </dl>

      {saved.length > 0 && (
        <section>
          <h3 className="bubble__heading">
            Saved {courseCountLabel(saved.length)}
          </h3>
          <ul className="course-rows">
            {saved.map((course) => (
              <li key={`${course.code}-${course.term}`} className="course-row">
                <span className="course-row__code">{course.code}</span>
                <span>{formatCourseStatus(course.status)}</span>
                <span className="course-row__credits">{course.grade}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {skipped.length > 0 && (
        <section>
          <h3 className="bubble__heading">
            Skipped {courseCountLabel(skipped.length)}
          </h3>
          <ul className="course-rows">
            {skipped.map((course, index) => (
              <li
                key={`${course.code}-${index}`}
                className="course-row course-row--two"
              >
                <span className="course-row__code">{course.code}</span>
                <span className="course-row__credits">{course.reason}</span>
              </li>
            ))}
          </ul>
          <p className="bubble__hint upload-result__note">
            Skipped courses weren't stored. They don't count toward your
            progress in CourseCompass, but they may still count toward your
            degree, for example if one was approved as a substitute for a
            required course. Check with your advisor.
          </p>
        </section>
      )}

      {clearedSubstitutions.length > 0 && (
        <div className="callout callout--warning" role="note">
          <p className="callout__title">
            {courseCountLabel(clearedSubstitutions.length)} of your
            substitutions no longer apply.
          </p>
          <p>
            {clearedSubstitutions
              .map((row) => `${row.substituteCode} for ${row.requirementCode}`)
              .join(', ')}
            . Match them again if they still apply.
          </p>
        </div>
      )}

      <div className="dialog__actions">
        <button type="button" className="button button--secondary"
          onClick={onAgain}>
          Upload another
        </button>
        <button type="button" className="button button--secondary"
          onClick={onMatch}>
          Match courses
        </button>
        <button type="button" className="button" onClick={onDone}>
          Done
        </button>
      </div>
    </div>
  );
}
