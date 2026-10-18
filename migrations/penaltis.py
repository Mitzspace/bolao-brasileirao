"""Migração SQLite idempotente com backup: pênaltis e provedor api-football.

- jogo.pode_penaltis; palpite.penaltis_casa/fora; resultado.penaltis_casa_real/fora_real;
- bolao.pontos_penaltis_exato (3) e pontos_penaltis_vencedor (1);
- campeonato.fonte_api ('football-data' em todos os campeonatos existentes).
Nenhum dado existente é alterado.

Uso: python -m migrations.penaltis instance/banco.db
PostgreSQL (Neon): aplique migrations/sql/011_penaltis.sql após backup.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

COLUNAS = {
    "jogo": [("pode_penaltis", "BOOLEAN NOT NULL DEFAULT 0")],
    "palpite": [("penaltis_casa", "INTEGER CHECK (penaltis_casa >= 0)"),
                ("penaltis_fora", "INTEGER CHECK (penaltis_fora >= 0)")],
    "resultado": [("penaltis_casa_real", "INTEGER"), ("penaltis_fora_real", "INTEGER")],
    "bolao": [("pontos_penaltis_exato", "INTEGER NOT NULL DEFAULT 3"),
              ("pontos_penaltis_vencedor", "INTEGER NOT NULL DEFAULT 1")],
    "campeonato": [("fonte_api", "VARCHAR(20) NOT NULL DEFAULT 'football-data'")],
}


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        faltando = [(t, c, d) for t, cols in COLUNAS.items()
                    for c, d in cols if c not in {r[1] for r in con.execute(f"PRAGMA table_info({t})")}]
        if not faltando:
            return None
        backup = path.with_name(path.name + ".penaltis-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        with con:
            for tabela, coluna, definicao in faltando:
                con.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
        return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    print(migrar(args.banco) or "Migração já aplicada.")
