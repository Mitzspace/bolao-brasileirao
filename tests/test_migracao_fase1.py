import sqlite3
from contextlib import closing

import pytest
from migrations.fase1 import ler, digest, construir, transformar, upgrade, rollback


def banco_legado(path):
    dados = {
        "participante": [dict(id=i, nome=n, email=f"{i}@teste.local", senha="hash-preservado", admin=i != 3)
                         for i, n in [(1, "William"), (22, "Ryan"), (3, "Albert")]],
        "campeonato": [dict(id=1, nome="BSA 2026", ano=2026, codigo_api="BSA")],
        "rodada": [dict(id=1, nome="1ª Rodada", aberta=1, campeonato_id=1)],
        "jogo": [dict(id=1, time_casa="A", time_fora="B", especial=1, encerrado=1,
                      data="2026-02-01 16:00:00", external_fonte="football-data.org", external_id="101", rodada_id=1)],
        "resultado": [dict(id=1, gols_casa_real=2, gols_fora_real=1, primeiro_gol_real=None, jogo_id=1)],
        "palpite": [dict(id=7, gols_casa=2, gols_fora=1, primeiro_gol=None, participante_id=3, jogo_id=1)],
        "bonus_rodada": [dict(id=5, participante_id=3, rodada_id=1, pontos=2, motivo="Bônus 1º Gol")],
        "classificacao_cache": [],
    }
    with closing(sqlite3.connect(path)) as con:
        for nome, rows in dados.items():
            if not rows:
                con.execute(f'CREATE TABLE "{nome}" (id INTEGER PRIMARY KEY, campeonato_id INTEGER, dados_json TEXT, atualizado_em TEXT)')
                continue
            cols = list(rows[0])
            con.execute(f'CREATE TABLE "{nome}" (' + ",".join(f'"{c}"' for c in cols) + ")")
            con.executemany(f'INSERT INTO "{nome}" VALUES (' + ",".join("?" for _ in cols) + ")", [[r[c] for c in cols] for r in rows])
        con.commit()
    return dados


def test_migracao_backup_reversao_idempotencia(tmp_path):
    path = tmp_path / "original.db"
    banco_legado(path)
    antes = ler(path)
    resumo = upgrade(path)
    novo = ler(path)
    assert resumo["pontos_totais"] == 7 and resumo["bonus_preservado"] == 2
    assert digest(ler(resumo["backup"])) == digest(antes)
    assert novo["palpite"][0]["id"] == 7 and novo["palpite"][0]["participacao_id"] == 3
    assert novo["palpite"][0]["origem"] is None and novo["palpite"][0]["criado_em"] is None
    assert novo["palpite_log"][0]["acao"] == "migracao"
    pessoas = {p["id"]: p for p in novo["participante"]}
    assert pessoas[1]["admin_global"] and not pessoas[22]["admin_global"]
    assert not pessoas[3]["conta_ativa"] and pessoas[3]["senha"] == "hash-preservado"
    part = next(p for p in novo["participacao"] if p["id"] == 3)
    assert part["papel"] == "responsavel" and part["usuario_id"] is None
    assert upgrade(path)["status"] == "já migrado"
    rollback(path, resumo["manifesto"])
    assert digest(ler(path)) == digest(antes)


def test_reversao_recusa_perda_de_dados_novos(tmp_path):
    path = tmp_path / "original.db"
    banco_legado(path)
    resumo = upgrade(path)
    with closing(sqlite3.connect(path)) as con:
        con.execute("UPDATE palpite SET gols_casa=3 WHERE id=7")
        con.commit()
    with pytest.raises(ValueError, match="dados novos/alterados"):
        rollback(path, resumo["manifesto"])
    assert ler(path)["palpite"][0]["gols_casa"] == 3


def test_transformacao_nao_altera_banco_e_recusa_ranking_diferente(tmp_path):
    path = tmp_path / "original.db"
    dados = banco_legado(path)
    original = path.read_bytes()
    dados["jogo"][0]["especial"] = 0
    dados["palpite"][0]["primeiro_gol"] = "Jogador"
    dados["resultado"][0]["primeiro_gol_real"] = "Jogador"
    with pytest.raises(ValueError, match="ranking mudaria"):
        transformar(dados)
    assert path.read_bytes() == original
