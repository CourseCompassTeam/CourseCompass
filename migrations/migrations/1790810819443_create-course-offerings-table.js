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
  pgm.createTable('course_offerings', {
    offering_id: {
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
    term: {
      type: 'varchar(20)',
      notNull: true,
    },
  });

  pgm.addConstraint('course_offerings', 'unique_course_term', {
    unique: ['course_id', 'term'],
  });

  pgm.createIndex('course_offerings', 'course_id');
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('course_offerings');
};
