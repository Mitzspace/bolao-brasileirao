-- PostgreSQL (Neon): aplicar após backup e ANTES de publicar o código novo.
-- Só ADICIONA uma coluna em bolao e a tabela corte_eliminacao. Nenhum dado existente é alterado.
-- Todos os bolões começam com a eliminação desligada.
BEGIN;

ALTER TABLE bolao ADD COLUMN IF NOT EXISTS eliminacao_participantes BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS corte_eliminacao (
    id SERIAL PRIMARY KEY,
    bolao_id INTEGER NOT NULL REFERENCES bolao (id),
    rodada_id INTEGER NOT NULL REFERENCES rodada (id),
    classificados INTEGER NOT NULL,
    CONSTRAINT unique_corte_bolao_rodada UNIQUE (bolao_id, rodada_id),
    CONSTRAINT corte_classificados CHECK (classificados > 0)
);

COMMIT;

-- Conferência:
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'bolao' AND column_name = 'eliminacao_participantes';
-- SELECT to_regclass('corte_eliminacao');
