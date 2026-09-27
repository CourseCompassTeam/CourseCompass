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
  pgm.createTable('syllabus_chunks', {
    chunk_id: {
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
    chunk_index: {
      type: 'integer',
      notNull: true,
    },
    chunk_text: {
      type: 'text',
      notNull: true,
    },
    embedding: {
      type: 'vector(768)',
      notNull: true,
    },
  });

  pgm.addConstraint('syllabus_chunks', 'unique_course_chunk_index', {
    unique: ['course_id', 'chunk_index'],
  });

  // ivfflat isn't part of node-pg-migrate's normal column/index API,
  // so this one needs raw SQL.
  pgm.sql(`
    CREATE INDEX idx_syllabus_chunks_embedding
    ON syllabus_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
  `);
};

/**
 * @param pgm {import('node-pg-migrate').MigrationBuilder}
 * @param run {() => void | undefined}
 * @returns {Promise<void> | void}
 */
export const down = (pgm) => {
  pgm.dropTable('syllabus_chunks');
};
