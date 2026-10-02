// Turns an 'audit' response's content into the numbers and course rows the
// audit bubble shows. Missing fields are tolerated, so a partial response
// still renders whatever it can.

/**
 * @param {object} content The audit response content.
 * @returns {{completed: ?number, required: ?number, remaining: ?number,
 *     percent: ?number, met: boolean, programName: ?string,
 *     missing: Array<{code: string, title: ?string, credits: ?number}>}}
 */
export function summarizeAudit(content = {}) {
  const {
    creditsCompleted,
    creditsRemaining,
    creditsRequired,
    requirementsMet,
    missingCourses = [],
    requiredCourses = [],
    programName,
  } = content;

  const completed = numberOrNull(creditsCompleted);
  const remaining = numberOrNull(creditsRemaining);
  let required = numberOrNull(creditsRequired);
  if (required == null && completed != null && remaining != null) {
    required = completed + remaining;
  }

  let percent = null;
  if (completed != null && required) {
    percent = Math.min(100, Math.max(0, Math.round((completed / required) * 100)));
  }

  // Add titles and credits to the bare course codes when the backend sent
  // the full course list.
  const byCode = new Map(requiredCourses.map((course) => [course.code, course]));
  const missing = missingCourses.map((code) => ({
    code,
    title: byCode.get(code)?.title ?? null,
    credits: numberOrNull(byCode.get(code)?.credits),
  }));

  return {
    completed,
    required,
    remaining,
    percent,
    met: requirementsMet === true,
    programName: programName ?? null,
    missing,
  };
}

function numberOrNull(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}
