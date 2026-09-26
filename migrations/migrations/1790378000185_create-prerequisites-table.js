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
  pgm.createTable('prerequisites', {
    prerequisite_id: {
      type: 'uuid',
      primaryKey: true,
      default: pgm.func('gen_random_uuid()'),
    },
    course_id: {
      type: 'uuid',
      notNull: true,
      references: 'courses',
      onDelete: 'CASCADE',
    },
    prerequisite_course_id: {
      type: 'uuid',
      notNull: true,
      references: 'courses',
      onDelete: 'CASCADE',
    },
    requirement_type: {
      type: 'varchar(20)',
      notNull: true,
      check: "requirement_type IN ('prereq', 'coreq')",
    },
  });

  pgm.addConstraint('prerequisites', 'no_self_prerequisite', {
    check: 'course_id <> prerequisite_course_id',
  });

  pgm.createIndex('prerequisites', 'course_id');
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('prerequisites');
};
