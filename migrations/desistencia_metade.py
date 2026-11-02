"""Migração SQLite idempotente com backup: desistência só até a metade do campeonato.

- bolao.desistencia_ate_metade: desligada em todos os bolões existentes (comportamento atual).
Nenhum dado existente é alterado.

Uso: python -m migrations.desistencia_metade instance/banco.db
PostgreSQL (Neon): aplique migrations/sql/013_desistencia_metade.sql após backup.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        if "desistencia_ate_metade" in {r[1] for r in con.execute("PRAGMA table_info(bolao)")}:
            return None
        backup = path.with_name(path.name + ".desistencia-metade-"
                                + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        with con:
            con.execute("ALTER TABLE bolao ADD COLUMN desistencia_ate_metade BOOLEAN NOT NULL DEFAULT 0")
        return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    print(migrar(args.banco) or "Migração já aplicada.")
