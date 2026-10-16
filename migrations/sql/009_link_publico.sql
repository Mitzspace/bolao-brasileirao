-- PostgreSQL (Neon): aplicar após backup e ANTES de publicar o código novo.
-- Só ADICIONA duas colunas na tabela bolao. Nenhum dado existente é alterado.
-- Todos os bolões começam com link público desligado e classificação oculta.
BEGIN;

-- Código aleatório do link público (vazio = link desligado).
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS codigo_publico VARCHAR(64);
CREATE UNIQUE INDEX IF NOT EXISTS ix_bolao_codigo_publico ON bolao (codigo_publico);

-- Classificação pública liberada até esta rodada, inclusive (vazio = oculta).
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS rodada_publica_id INTEGER REFERENCES rodada (id);

COMMIT;

-- Conferência (deve listar as duas colunas):
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'bolao' AND column_name IN ('codigo_publico', 'rodada_publica_id');
