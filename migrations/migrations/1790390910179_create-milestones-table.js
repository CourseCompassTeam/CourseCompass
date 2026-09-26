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
  pgm.createTable('milestones', {
    milestone_id: { type: 'uuid', primaryKey: true, default: pgm.func('gen_random_uuid()') },
    credit_min: { type: 'integer', notNull: true },
    credit_max: { type: 'integer' },
    label: { type: 'varchar(100)', notNull: true },
    next_actions: { type: 'text[]', notNull: true, default: pgm.func("'{}'") },
  });
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('milestones');
};
