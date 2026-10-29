/**
 * @type {import('node-pg-migrate').ColumnDefinitions | undefined}
 */
export const shorthands = undefined;

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 * A legacy course (from the old catalog) counts as the current course it replaced.
 * Schema only: the rows come from the seed script (dev/test) or are inserted by hand.
 */
export const up = (pgm) => {
  pgm.createTable("course_equivalencies", {
    equivalency_id: {
      type: "uuid",
      primaryKey: true,
      default: pgm.func("gen_random_uuid()"),
    },
    legacy_course_id: {
      type: "uuid",
      notNull: true,
      references: "courses(course_id)",
      onDelete: "RESTRICT",
    },
    replaces_course_id: {
      type: "uuid",
      notNull: true,
      references: "courses(course_id)",
      onDelete: "RESTRICT",
    },
  });
  pgm.addConstraint("course_equivalencies", "unique_legacy_replaces", {
    unique: ["legacy_course_id", "replaces_course_id"],
  });
  pgm.addConstraint("course_equivalencies", "check_legacy_differs_from_replaced", {
    check: "legacy_course_id <> replaces_course_id",
  });
  // legacy_course_id is covered by the unique constraint above (it leads with it).
  pgm.createIndex("course_equivalencies", "replaces_course_id");
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable("course_equivalencies");
};
