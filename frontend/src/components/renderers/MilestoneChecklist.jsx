// Next steps outside of class (US-07): one checklist per milestone.

/**
 * Formats a milestone's credit band, e.g. "0–12 credits" or "25+ credits".
 * @param {?number} min Lowest credits in the band.
 * @param {?number} max Highest credits in the band, or null for no limit.
 * @returns {string} The label, or '' if the band is unknown.
 */
export function formatCreditBand(min, max) {
  if (min == null && max == null) {
    return '';
  }
  if (max == null) {
    return `${min}+ credits`;
  }
  return `${min ?? 0}–${max} credits`;
}

/**
 * @param {{milestones: Array<{label: string, creditMin: ?number,
 *     creditMax: ?number, nextActions: string[]}>}} props
 */
export default function MilestoneChecklist({ milestones }) {
  return (
    <div className="milestones">
      {milestones.map((milestone) => {
        const band = formatCreditBand(milestone.creditMin, milestone.creditMax);
        return (
          <section key={milestone.label} className="milestone">
            <h3 className="milestone__header">
              <span className="milestone__label">{milestone.label}</span>
              {band && <span className="milestone__band">{band}</span>}
            </h3>
            <ul className="checklist">
              {(milestone.nextActions ?? []).map((action) => (
                <li key={action} className="checklist__item">
                  <span className="checklist__box" aria-hidden="true" />
                  {action}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
