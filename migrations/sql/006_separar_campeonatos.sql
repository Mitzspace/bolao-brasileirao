-- PostgreSQL (Neon): cada campeonato vira um bolão separado. Faça backup antes.
-- Pode rodar mais de uma vez (na segunda não muda nada).
-- 1) Mostra o que será alterado (opcional):
--    SELECT f.id, f.nome, c.nome AS campeonato, c.ano FROM bolao f
--    JOIN campeonato c ON c.id = f.campeonato_id WHERE f.grupo_id IS NOT NULL;
BEGIN;
-- Bolão extra com o mesmo nome do principal passa a se chamar "<campeonato> <temporada>".
UPDATE bolao AS f
   SET nome = LEFT(c.nome || COALESCE(' ' || c.ano::text, ''), 100)
  FROM bolao AS p, campeonato AS c
 WHERE f.grupo_id = p.id AND c.id = f.campeonato_id AND f.nome = p.nome;
UPDATE bolao SET grupo_id = NULL WHERE grupo_id IS NOT NULL;
COMMIT;
