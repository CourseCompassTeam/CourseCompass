/**
 * @type {import('node-pg-migrate').ColumnDefinitions | undefined}
 */
export const shorthands = undefined;

/**
 * Data fix: the old-catalog courses MSSE 600, 663 and 670 are kept as
 * inactive courses so transcripts that contain them can be saved and used
 * as substitutes. Each one maps to the current course it replaced.
 *
 * Idempotent: existing rows are left alone. Dev seeds already have these
 * rows; production did not.
 *
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const up = (pgm) => {
  pgm.sql(`
    INSERT INTO courses (code, title, description, credits, is_active)
    VALUES
      ('MSSE 600', 'Introduction to Software Engineering', NULL, 3, false),
      ('MSSE 663', 'Web Frameworks', NULL, 3, false),
      ('MSSE 670', 'Java Software Development', NULL, 3, false)
    ON CONFLICT (code) DO NOTHING;
  `);

  pgm.sql(`
    INSERT INTO course_equivalencies (legacy_course_id, replaces_course_id)
    SELECT legacy.course_id, current.course_id
    FROM (VALUES
      ('MSSE 600', 'MSSE 601'),
      ('MSSE 663', 'MSES 602'),
      ('MSSE 670', 'MSCC 697')
    ) AS pairs(legacy_code, current_code)
    JOIN courses legacy ON legacy.code = pairs.legacy_code
    JOIN courses current ON current.code = pairs.current_code
    ON CONFLICT (legacy_course_id, replaces_course_id) DO NOTHING;
  `);
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.sql(`
    DELETE FROM course_equivalencies
    WHERE legacy_course_id IN (
      SELECT course_id FROM courses WHERE code IN ('MSSE 600', 'MSSE 663', 'MSSE 670')
    );
  `);
  pgm.sql(`
    DELETE FROM courses
    WHERE code IN ('MSSE 600', 'MSSE 663', 'MSSE 670') AND is_active = false;
  `);
};
