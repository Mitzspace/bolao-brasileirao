-- PostgreSQL (Neon): aplicar após backup e ANTES de publicar o código novo.
-- Regras de pontuação por bolão. Os bolões existentes ficam com os valores atuais.
BEGIN;
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS pontos_comum_exato INTEGER NOT NULL DEFAULT 3;
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS pontos_comum_resultado INTEGER NOT NULL DEFAULT 1;
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS pontos_classico_exato INTEGER NOT NULL DEFAULT 5;
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS pontos_classico_resultado INTEGER NOT NULL DEFAULT 3;
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS pontos_primeiro_gol INTEGER NOT NULL DEFAULT 2;
COMMIT;
