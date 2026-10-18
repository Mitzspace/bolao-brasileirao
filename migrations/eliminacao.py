"""Migração SQLite idempotente com backup: eliminação de participantes por fase.

- bolao.eliminacao_participantes: liga a eliminação (desligada em todos os bolões existentes).
- corte_eliminacao: após a rodada indicada, só os N melhores seguem no ranking.
Nenhum dado existente é alterado.

Uso: python -m migrations.eliminacao instance/banco.db
PostgreSQL (Neon): aplique migrations/sql/010_eliminacao.sql após backup.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        tem_coluna = "eliminacao_participantes" in {r[1] for r in con.execute("PRAGMA table_info(bolao)")}
        tem_tabela = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='corte_eliminacao'").fetchone()
        if tem_coluna and tem_tabela:
            return None
        backup = path.with_name(path.name + ".eliminacao-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        with con:
            if not tem_coluna:
                con.execute("ALTER TABLE bolao ADD COLUMN eliminacao_participantes BOOLEAN NOT NULL DEFAULT 0")
            con.execute("""CREATE TABLE IF NOT EXISTS corte_eliminacao (
                id INTEGER NOT NULL PRIMARY KEY,
                bolao_id INTEGER NOT NULL REFERENCES bolao (id),
                rodada_id INTEGER NOT NULL REFERENCES rodada (id),
                classificados INTEGER NOT NULL,
                CONSTRAINT unique_corte_bolao_rodada UNIQUE (bolao_id, rodada_id),
                CONSTRAINT corte_classificados CHECK (classificados > 0))""")
        return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    print(migrar(args.banco) or "Migração já aplicada.")
