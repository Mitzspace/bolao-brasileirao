"""Migração SQLite idempotente com backup: link público de consulta por bolão.

- bolao.codigo_publico: código aleatório do link (vazio = link desligado).
- bolao.rodada_publica_id: classificação pública liberada até esta rodada (vazio = oculta).
Nenhum dado existente é alterado; todos os bolões começam com link desligado e tabela oculta.

Uso: python -m migrations.link_publico instance/banco.db
PostgreSQL (Neon): aplique migrations/sql/009_link_publico.sql após backup.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        colunas = {r[1] for r in con.execute("PRAGMA table_info(bolao)")}
        if {"codigo_publico", "rodada_publica_id"} <= colunas:
            return None
        backup = path.with_name(path.name + ".publico-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        with con:
            if "codigo_publico" not in colunas:
                con.execute("ALTER TABLE bolao ADD COLUMN codigo_publico VARCHAR(64)")
                con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_bolao_codigo_publico ON bolao (codigo_publico)")
            if "rodada_publica_id" not in colunas:
                con.execute("ALTER TABLE bolao ADD COLUMN rodada_publica_id INTEGER REFERENCES rodada(id)")
        return backup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    print(migrar(args.banco) or "Migração já aplicada.")
