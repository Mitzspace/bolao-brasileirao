-- PostgreSQL (Neon): aplicar após backup e ANTES de publicar o código novo.
-- Permite vários campeonatos no mesmo bolão (cada campeonato é um bolão ligado ao principal).
BEGIN;
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS grupo_id INTEGER REFERENCES bolao(id);
COMMIT;
