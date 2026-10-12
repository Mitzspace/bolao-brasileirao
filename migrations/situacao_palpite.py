"""Migração SQLite idempotente com backup. Execute com o caminho do banco."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        if "situacao" in {r[1] for r in con.execute("PRAGMA table_info(palpite)")}:
            return None
        backup = path.with_name(path.name + ".situacao-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        with con:
            con.execute("ALTER TABLE palpite ADD COLUMN situacao VARCHAR(20) NOT NULL DEFAULT 'valido' CHECK (situacao IN ('valido', 'nao_enviado', 'fora_prazo'))")
        return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    print(migrar(args.banco) or "Migração já aplicada.")
