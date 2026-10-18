-- PostgreSQL (Neon): aplicar após backup e ANTES de publicar o código novo.
-- Só ADICIONA colunas. Nenhum dado existente é alterado.
BEGIN;

ALTER TABLE jogo ADD COLUMN IF NOT EXISTS pode_penaltis BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE palpite ADD COLUMN IF NOT EXISTS penaltis_casa INTEGER;
ALTER TABLE palpite ADD COLUMN IF NOT EXISTS penaltis_fora INTEGER;
ALTER TABLE palpite DROP CONSTRAINT IF EXISTS palpite_penaltis;
ALTER TABLE palpite ADD CONSTRAINT palpite_penaltis CHECK (
    (penaltis_casa IS NULL AND penaltis_fora IS NULL) OR (penaltis_casa >= 0 AND penaltis_fora >= 0));

ALTER TABLE resultado ADD COLUMN IF NOT EXISTS penaltis_casa_real INTEGER;
ALTER TABLE resultado ADD COLUMN IF NOT EXISTS penaltis_fora_real INTEGER;

ALTER TABLE bolao ADD COLUMN IF NOT EXISTS pontos_penaltis_exato INTEGER NOT NULL DEFAULT 3;
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS pontos_penaltis_vencedor INTEGER NOT NULL DEFAULT 1;

ALTER TABLE campeonato ADD COLUMN IF NOT EXISTS fonte_api VARCHAR(20) NOT NULL DEFAULT 'football-data';

COMMIT;
