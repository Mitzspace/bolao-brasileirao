-- PostgreSQL: aplicar após backup e antes de publicar o código.
BEGIN;
ALTER TABLE participacao ADD COLUMN IF NOT EXISTS email VARCHAR(100);
COMMIT;
