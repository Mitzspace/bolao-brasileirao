"""Verifica SQLite sem reconstruir tabelas: VARCHAR não limita textos nesse banco.

Uso: python -m migrations.codigo_api_espn instance/banco.db
PostgreSQL: aplique migrations/sql/012_codigo_api_espn.sql após backup.
"""
import argparse
from contextlib import closing
from pathlib import Path
import sqlite3


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as con:
        colunas = {r[1] for r in con.execute('PRAGMA table_info(campeonato)')}
        if not {'codigo_api', 'fonte_api'}.issubset(colunas):
            raise ValueError('Aplique as migrações anteriores, incluindo penaltis, antes desta verificação.')
    return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('banco')
    args = parser.parse_args()
    migrar(args.banco)
    print('SQLite já aceita códigos de 40 caracteres; nenhuma alteração necessária.')
