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
  pgm.createTable('schedules', {
    schedule_id: { type: 'uuid', primaryKey: true, default: pgm.func('gen_random_uuid()') },
    student_id: { type: 'uuid', notNull: true, references: 'students', onDelete: 'CASCADE' },
    status: { type: 'varchar(20)', notNull: true, default: 'draft', check: "status IN ('draft', 'exported')" },
    created_at: { type: 'timestamptz', notNull: true, default: pgm.func('now()') },
  });
  pgm.createIndex('schedules', 'student_id');
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('schedules');
};
