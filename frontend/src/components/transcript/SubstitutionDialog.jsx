import { useEffect, useId, useRef, useState } from 'react';

import SubstitutionMatcher from './SubstitutionMatcher.jsx';

/**
 * Works out which declarations to add, change, or remove so the saved
 * substitutions match what the student set in the matcher.
 *
 * @param {Array<{substitutionId: string, requirementCode: string,
 *     substituteCode: string}>} substitutions Declarations as loaded.
 * @param {Record<string, string>} assignments Requirement code to course
 *     code, as the matcher reports them on save.
 * @returns {{
 *   removals: string[],
 *   declarations: Array<{requirementCode: string, substituteCode: string}>,
 * }}
 */
export function diffSubstitutions(substitutions, assignments) {
  const removals = [];
  const declarations = [];
  const byRequirement = new Map(
    substitutions.map((row) => [row.requirementCode, row]),
  );

  for (const row of substitutions) {
    if (!assignments[row.requirementCode]) {
      removals.push(row.substitutionId);
    }
  }
  for (const [requirementCode, substituteCode] of Object.entries(assignments)) {
    const existing = byRequirement.get(requirementCode);
    if (!existing || existing.substituteCode !== substituteCode) {
      declarations.push({ requirementCode, substituteCode });
    }
  }
  return { removals, declarations };
}

/**
 * Modal for matching transcript courses to missing requirements.
 * Loads the review when it opens, and saves each change through the
 * transcript service.
 *
 * @param {{
 *   transcriptService: import('../../services/transcriptService.js')
 *       .TranscriptService,
 *   isOpen: boolean,
 *   onClose: () => void,
 * }} props
 */
export default function SubstitutionDialog({
  transcriptService,
  isOpen,
  onClose,
}) {
  const dialogRef = useRef(null);
  const titleId = useId();
  const [review, setReview] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen && !dialog.open) {
      dialog.showModal();
      loadReview();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
    // loadReview is stable for this component's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  async function loadReview() {
    setError(null);
    setIsLoading(true);
    try {
      setReview(await transcriptService.getSubstitutionReview());
    } catch (loadError) {
      setError(loadError);
    } finally {
      setIsLoading(false);
    }
  }

  async function save(assignments) {
    if (!review) return;
    const { removals, declarations } = diffSubstitutions(
      review.substitutions,
      assignments,
    );
    setError(null);
    setIsSaving(true);
    try {
      for (const substitutionId of removals) {
        await transcriptService.removeSubstitution(substitutionId);
      }
      for (const { requirementCode, substituteCode } of declarations) {
        await transcriptService.declareSubstitution(
          requirementCode,
          substituteCode,
        );
      }
      onClose();
    } catch (saveError) {
      setError(saveError);
      // Reload so the matcher reflects what was actually saved.
      await loadReview();
    } finally {
      setIsSaving(false);
    }
  }

  const initialAssignments = Object.fromEntries(
    (review?.substitutions ?? []).map((row) => [
      row.requirementCode,
      row.substituteCode,
    ]),
  );
  const hasWork = (review?.requirements.length ?? 0) > 0
    && (review?.courses.length ?? 0) > 0;

  return (
    <dialog
      ref={dialogRef}
      className="dialog dialog--wide"
      aria-labelledby={titleId}
      onClose={onClose}
      onCancel={(event) => {
        if (isSaving) event.preventDefault();
      }}
    >
      <div className="dialog__header">
        <h2 id={titleId} className="dialog__title">Match transcript courses</h2>
        <button
          type="button"
          className="dialog__close"
          onClick={onClose}
          disabled={isSaving}
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div className="dialog__body">
        {isLoading && <p role="status">Loading your courses…</p>}

        {error && (
          <div className="callout callout--error" role="alert">
            <p>{error.message}</p>
          </div>
        )}

        {!isLoading && review && !hasWork && (
          <p>
            Nothing to match right now. Every required course is either
            completed or has no transcript course left to apply.
          </p>
        )}

        {!isLoading && review && hasWork && (
          <SubstitutionMatcher
            key={JSON.stringify(review.substitutions)}
            requirements={review.requirements}
            courses={review.courses}
            initialAssignments={initialAssignments}
            onSave={save}
          />
        )}
      </div>
    </dialog>
  );
}
