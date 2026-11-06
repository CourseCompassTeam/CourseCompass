/**
 * @type {import('node-pg-migrate').ColumnDefinitions | undefined}
 */
export const shorthands = undefined;

/**
 * A student-declared substitute: the student took `substitute_course_id`
 * in place of the required course `requirement_course_id`. One per
 * requirement per student (one-for-one). Declarations are advisor-verified
 * by the student; the app does not approve them.
 *
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const up = (pgm) => {
  pgm.createTable('student_substitutions', {
    substitution_id: {
      type: 'uuid',
      primaryKey: true,
      default: pgm.func('gen_random_uuid()'),
    },
    student_id: {
      type: 'uuid',
      notNull: true,
      references: 'students',
      onDelete: 'CASCADE',
    },
    requirement_course_id: {
      type: 'uuid',
      notNull: true,
      references: 'courses',
      onDelete: 'RESTRICT',
    },
    substitute_course_id: {
      type: 'uuid',
      notNull: true,
      references: 'courses',
      onDelete: 'RESTRICT',
    },
    source: {
      type: 'varchar(20)',
      notNull: true,
      default: 'student',
      check: "source IN ('student')",
    },
    created_at: {
      type: 'timestamptz',
      notNull: true,
      default: pgm.func('now()'),
    },
  });

  pgm.addConstraint('student_substitutions', 'unique_student_requirement', {
    unique: ['student_id', 'requirement_course_id'],
  });
  pgm.addConstraint('student_substitutions', 'check_substitute_differs', {
    check: 'requirement_course_id <> substitute_course_id',
  });
  pgm.createIndex('student_substitutions', 'substitute_course_id');
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('student_substitutions');
};
