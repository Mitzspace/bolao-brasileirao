"""Zonas da tabela ESPN: grupos sem `note` herdam a zona da mesma posição dos outros grupos."""
from services.classificacao import _processar_resposta

ZONA_1 = {"nome": "Oitavas de final", "cor": "#4ade80"}
ZONA_2 = {"nome": "Playoffs da Sul-Americana", "cor": "#86efac"}


def _linha(pos, nome, zona=None):
    return {"position": pos, "team": {"id": f"espn:{pos}", "name": nome, "shortName": nome},
            "points": 10 - pos, "playedGames": 6, "won": 2, "draw": 2, "lost": 2,
            "goalsFor": 5, "goalsAgainst": 5, "goalDifference": 0, "_zona": zona}


def _payload():
    return {
        "competition": {"name": "Sul-Americana", "code": "conmebol.sudamericana"},
        "season": {"startDate": "2026-01-01"},
        "standings": [
            {"stage": "GROUP_STAGE", "type": "TOTAL", "group": "Grupo A", "table": [
                _linha(1, "A1", ZONA_1), _linha(2, "A2", ZONA_2), _linha(3, "A3"), _linha(4, "A4")]},
            {"stage": "GROUP_STAGE", "type": "TOTAL", "group": "Grupo B", "table": [
                _linha(1, "B1"), _linha(2, "B2"), _linha(3, "B3"), _linha(4, "B4")]},
        ],
    }


def test_grupo_sem_zona_herda_a_do_mesmo_posto():
    r = _processar_resposta(_payload(), "conmebol.sudamericana")
    grupo_a, grupo_b = r["grupos"]
    assert [l["zona"]["cor"] if l["zona"] else None for l in grupo_a["linhas"]] == ["#4ade80", "#86efac", None, None]
    assert [l["zona"]["cor"] if l["zona"] else None for l in grupo_b["linhas"]] == ["#4ade80", "#86efac", None, None]
    assert [(z["nome"], z["faixa"]) for z in r["legendas"]] == [
        ("Oitavas de final", (1, 1)), ("Playoffs da Sul-Americana", (2, 2))]


def test_grupo_unico_nao_inventa_zona():
    dados = _payload()
    dados["standings"] = dados["standings"][1:]
    r = _processar_resposta(dados, "conmebol.sudamericana")
    assert all(l["zona"] is None for l in r["grupos"][0]["linhas"])
