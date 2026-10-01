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
  pgm.createTable('terms', {
    term_id: {
      type: 'uuid',
      primaryKey: true,
      default: pgm.func('gen_random_uuid()'),
    },
    term_name: {
      type: 'varchar(20)',
      notNull: true,
      unique: true,
    },
    start_date: {
      type: 'date',
      notNull: true,
    },
    end_date: {
      type: 'date',
      notNull: true,
    },
  });

  // course_offerings is dev/seed data only, safe to clear and rebuild.
  pgm.sql('DELETE FROM course_offerings;');

  pgm.dropConstraint('course_offerings', 'unique_course_term');
  pgm.dropColumn('course_offerings', 'term');
  pgm.addColumn('course_offerings', {
    term_id: {
      type: 'uuid',
      notNull: true,
      references: 'terms',
      onDelete: 'CASCADE',
    },
  });
  pgm.addConstraint('course_offerings', 'unique_course_term', {
    unique: ['course_id', 'term_id'],
  });
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropConstraint('course_offerings', 'unique_course_term');
  pgm.dropColumn('course_offerings', 'term_id');
  pgm.addColumn('course_offerings', {
    term: {
      type: 'varchar(20)',
      notNull: true,
    },
  });
  pgm.addConstraint('course_offerings', 'unique_course_term', {
    unique: ['course_id', 'term'],
  });
  pgm.dropTable('terms');
};
