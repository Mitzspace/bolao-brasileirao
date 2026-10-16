-- PostgreSQL (Neon): aplicar após backup e ANTES de publicar o código novo.
-- Só ADICIONA: uma coluna nova (jogo.ordem) e índices. Nenhum palpite, resultado
-- ou pontuação é alterado. O código antigo continua funcionando com estas mudanças.
--
-- 1) jogo.ordem = posição do jogo na aba da planilha. Nas rodadas que já têm
--    palpites (1ª a 30ª, importadas da planilha), a ordem de cadastro é a ordem
--    da planilha (conferido rodada a rodada). Rodadas sem palpites (31ª em diante,
--    vindas da API) ficam com ordem nula e são exibidas por data e horário.
-- 2) Índices nas chaves usadas pelas telas (jogos por rodada, palpites por jogo...).
BEGIN;

ALTER TABLE jogo ADD COLUMN IF NOT EXISTS ordem INTEGER;

UPDATE jogo AS j
SET ordem = x.posicao
FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY rodada_id ORDER BY id) AS posicao
    FROM jogo
    WHERE rodada_id IN (
        SELECT DISTINCT jg.rodada_id FROM palpite AS p JOIN jogo AS jg ON jg.id = p.jogo_id
    )
) AS x
WHERE j.id = x.id AND j.ordem IS NULL;

CREATE INDEX IF NOT EXISTS ix_jogo_rodada_id ON jogo (rodada_id);
CREATE INDEX IF NOT EXISTS ix_palpite_jogo_id ON palpite (jogo_id);
CREATE INDEX IF NOT EXISTS ix_rodada_campeonato_id ON rodada (campeonato_id);
CREATE INDEX IF NOT EXISTS ix_palpite_log_palpite_id ON palpite_log (palpite_id);
CREATE INDEX IF NOT EXISTS ix_participacao_log_participacao_id ON participacao_log (participacao_id);

COMMIT;

-- Conferência (deve mostrar 30 rodadas com ordem e 8 sem):
-- SELECT COUNT(DISTINCT rodada_id) FILTER (WHERE ordem IS NOT NULL) AS com_ordem,
--        COUNT(DISTINCT rodada_id) FILTER (WHERE ordem IS NULL) AS sem_ordem
-- FROM jogo;
