"""Migração SQLite idempotente com backup: regras de pontuação por bolão.

Todo bolão existente recebe os valores atuais (comum 3/1, clássico 5/3, primeiro gol +2),
então nenhuma pontuação muda até alguém editar as regras.

Uso: python -m migrations.regras_bolao instance/banco.db
PostgreSQL (Neon): aplique migrations/sql/007_regras_bolao.sql após backup.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

COLUNAS = (("pontos_comum_exato", 3), ("pontos_comum_resultado", 1), ("pontos_classico_exato", 5),
           ("pontos_classico_resultado", 3), ("pontos_primeiro_gol", 2))


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        existentes = {r[1] for r in con.execute("PRAGMA table_info(bolao)")}
        faltando = [(nome, padrao) for nome, padrao in COLUNAS if nome not in existentes]
        if not faltando:
            return None
        backup = path.with_name(path.name + ".regras-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        with con:
            for nome, padrao in faltando:
                con.execute(f"ALTER TABLE bolao ADD COLUMN {nome} INTEGER NOT NULL DEFAULT {padrao}")
        return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    print(migrar(args.banco) or "Migração já aplicada.")
