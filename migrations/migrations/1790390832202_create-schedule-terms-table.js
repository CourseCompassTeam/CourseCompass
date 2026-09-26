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
  pgm.createTable('schedule_terms', {
    schedule_term_id: { type: 'uuid', primaryKey: true, default: pgm.func('gen_random_uuid()') },
    schedule_id: { type: 'uuid', notNull: true, references: 'schedules', onDelete: 'CASCADE' },
    term_name: { type: 'varchar(20)', notNull: true },
    term_order: { type: 'integer', notNull: true },
  });
  pgm.addConstraint('schedule_terms', 'unique_schedule_term_order', { unique: ['schedule_id', 'term_order'] });
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('schedule_terms');
};
