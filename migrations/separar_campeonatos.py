"""Cada campeonato vira um bolão separado: desfaz os grupos criados por grupo_id.

Bolões extras que tinham o mesmo nome do bolão principal passam a se chamar
"<campeonato> <temporada>" (ex.: "Copa do Brasil 2026") para não ficarem com nomes
iguais. Nenhum palpite, jogo, participante ou ponto é alterado.

Uso local (SQLite, com backup):  python -m migrations.separar_campeonatos instance/banco.db
PostgreSQL (Neon): aplique migrations/sql/006_separar_campeonatos.sql após backup.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def migrar(caminho):
    path = Path(caminho).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as con:
        agrupados = con.execute(
            "SELECT f.id, f.nome, p.nome, c.nome, c.ano FROM bolao f JOIN bolao p ON p.id = f.grupo_id "
            "JOIN campeonato c ON c.id = f.campeonato_id").fetchall()
        if not agrupados:
            return None, []
        backup = path.with_name(path.name + ".separar-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") + ".bak")
        with closing(sqlite3.connect(backup)) as copia:
            con.backup(copia)
        renomeados = []
        with con:
            for id_, nome, nome_principal, campeonato, ano in agrupados:
                if nome == nome_principal:
                    novo = f"{campeonato} {ano}" if ano else campeonato
                    con.execute("UPDATE bolao SET nome = ? WHERE id = ?", (novo[:100], id_))
                    renomeados.append((nome, novo[:100]))
            con.execute("UPDATE bolao SET grupo_id = NULL WHERE grupo_id IS NOT NULL")
        return backup, renomeados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("banco")
    args = parser.parse_args()
    backup, renomeados = migrar(args.banco)
    if backup is None:
        print("Nada a fazer: nenhum campeonato estava agrupado.")
    else:
        print(f"Campeonatos separados. Backup: {backup}")
        for antes, depois in renomeados:
            print(f'  bolão renomeado: "{antes}" -> "{depois}"')
