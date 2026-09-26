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
  pgm.createTable('requirements', {
    requirement_id: {
      type: 'uuid',
      primaryKey: true,
      default: pgm.func('gen_random_uuid()'),
    },
    program_id: {
      type: 'uuid',
      notNull: true,
      references: 'programs',
      onDelete: 'CASCADE',
    },
    course_id: {
      type: 'uuid',
      references: 'courses',
      onDelete: 'SET NULL',
    },
    category: {
      type: 'varchar(20)',
      notNull: true,
      check: "category IN ('core', 'elective')",
    },
    credits_required: {
      type: 'integer',
      notNull: true,
      check: 'credits_required > 0',
    },
  });

  pgm.createIndex('requirements', 'program_id');
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('requirements');
};
