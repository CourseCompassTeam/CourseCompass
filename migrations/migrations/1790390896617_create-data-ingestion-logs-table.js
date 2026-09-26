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
  pgm.createTable('data_ingestion_logs', {
    log_id: { type: 'uuid', primaryKey: true, default: pgm.func('gen_random_uuid()') },
    source: { type: 'varchar(50)', notNull: true, check: "source IN ('course_catalog', 'transcript')" },
    started_at: { type: 'timestamptz', notNull: true, default: pgm.func('now()') },
    completed_at: { type: 'timestamptz' },
    status: { type: 'varchar(20)', notNull: true, check: "status IN ('running', 'succeeded', 'failed')" },
    records_processed: { type: 'integer' },
    error_message: { type: 'text' },
  });
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('data_ingestion_logs');
};
