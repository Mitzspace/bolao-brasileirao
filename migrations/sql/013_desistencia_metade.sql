-- PostgreSQL (Neon): aplicar após backup e ANTES de publicar o código novo.
-- Só ADICIONA uma coluna em bolao. Nenhum dado existente é alterado.
-- Todos os bolões começam com a regra desligada (comportamento atual).
BEGIN;

ALTER TABLE bolao ADD COLUMN IF NOT EXISTS desistencia_ate_metade BOOLEAN NOT NULL DEFAULT false;

COMMIT;

-- Conferência:
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'bolao' AND column_name = 'desistencia_ate_metade';
