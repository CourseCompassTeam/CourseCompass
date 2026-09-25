/**
 * @type {import('node-pg-migrate').ColumnDefinitions | undefined}
 */
export const shorthands = undefined;

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const up = (pgm) => {
  pgm.createTable('transcript_entries', {
    entry_id: {
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
    course_id: {
      type: 'uuid',
      notNull: true,
      references: 'courses',
      onDelete: 'RESTRICT',
    },
    term: {
      type: 'varchar(20)',
      notNull: true,
    },
    status: {
      type: 'varchar(20)',
      notNull: true,
      check: "status IN ('completed', 'in_progress', 'planned')",
    },
  });

  pgm.createIndex('transcript_entries', 'student_id');
  pgm.createIndex('transcript_entries', 'course_id');
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('transcript_entries');
};
