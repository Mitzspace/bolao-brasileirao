"""Migração SQLite idempotente com backup: ordem fixa dos jogos e índices de desempenho.

- Cria jogo.ordem (posição do jogo na aba da planilha). Nas rodadas que já têm
  palpites (as que vieram da planilha), a ordem atual de cadastro vira a posição,
  que é exatamente a ordem da planilha. As demais rodadas ficam sem posição e
  passam a ser exibidas por data e horário (jogos da API).
- Cria índices nas chaves usadas pelas telas. Não altera nenhum palpite ou resultado.

Uso: python -m migrations.ordem_jogo instance/banco.db
PostgreSQL (Neon): aplique migrations/sql/008_ordem_jogo_indices.sql após backup.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

INDICES = (
    ("ix_jogo_rodada_id", "jogo", "rodada_id"),
    ("ix_palpite_jogo_id", "palpite", "jogo_id"),
    ("ix_rodada_campeonato_id", "rodada", "campeonato_id"),
    ("ix_palpite_log_palpite_id", "palpite_log", "palpite_id"),
    ("ix_participacao_log_participacao_id", "participacao_log", "participacao_id"),
)

PREENCHER_ORDEM = """
UPDATE jogo SET ordem = (
    SELECT COUNT(*) FROM jogo AS anterior
    WHERE anterior.rodada_id = jogo.rodada_id AND anterior.id <= jogo.id
)
WHERE ordem IS NULL AND rodada_id IN (
    SELECT DISTINCT j.rodada_id FROM palpite AS p JOIN jogo AS j ON j.id = p.jogo_id
)
"""


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        colunas = {r[1] for r in con.execute("PRAGMA table_info(jogo)")}
        indices = {r[1] for r in con.execute("SELECT type, name FROM sqlite_master WHERE type = 'index'")}
        faltando = [i for i in INDICES if i[0] not in indices]
        if "ordem" in colunas and not faltando:
            return None
        backup = path.with_name(path.name + ".ordem-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        with con:
            if "ordem" not in colunas:
                con.execute("ALTER TABLE jogo ADD COLUMN ordem INTEGER")
                con.execute(PREENCHER_ORDEM)
            for nome, tabela, coluna in faltando:
                con.execute(f"CREATE INDEX IF NOT EXISTS {nome} ON {tabela} ({coluna})")
        return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    print(migrar(args.banco) or "Migração já aplicada.")
