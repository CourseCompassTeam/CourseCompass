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
  pgm.createTable('schedule_items', {
    schedule_item_id: { type: 'uuid', primaryKey: true, default: pgm.func('gen_random_uuid()') },
    schedule_term_id: { type: 'uuid', notNull: true, references: 'schedule_terms', onDelete: 'CASCADE' },
    course_id: { type: 'uuid', notNull: true, references: 'courses', onDelete: 'RESTRICT' },
  });
  pgm.addConstraint('schedule_items', 'unique_term_course', { unique: ['schedule_term_id', 'course_id'] });
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('schedule_items');
};
