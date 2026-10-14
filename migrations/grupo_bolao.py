"""Migração SQLite idempotente com backup: vários campeonatos no mesmo bolão (bolao.grupo_id).

Uso: python -m migrations.grupo_bolao instance/banco.db
PostgreSQL (Neon): aplique migrations/sql/005_grupo_bolao.sql após backup.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        if "grupo_id" in {r[1] for r in con.execute("PRAGMA table_info(bolao)")}:
            return None
        backup = path.with_name(path.name + ".grupo-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        with con:
            con.execute("ALTER TABLE bolao ADD COLUMN grupo_id INTEGER REFERENCES bolao(id)")
        return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    print(migrar(args.banco) or "Migração já aplicada.")
