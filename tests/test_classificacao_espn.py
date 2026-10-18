"""Tabela de classificação de campeonatos ESPN (services/classificacao_espn.py)."""
import gzip
import io
import json
from datetime import datetime, timedelta
from unittest.mock import patch

from flask import g

from database import db
from models import Campeonato, ClassificacaoCache
from services import classificacao_espn
from services.escudos import escudo_time
from services.importador_espn import ErroEspn
from services.tabela_campeonato import dados_tabela


def entrada(tid, nome, rank, pontos, note=None, curto=None):
    stats = {"gamesPlayed": 6, "wins": pontos // 3, "ties": pontos % 3, "losses": 1, "points": pontos,
             "pointsFor": 8, "pointsAgainst": 5, "pointDifferential": 3, "rank": rank}
    return {"team": {"id": str(tid), "displayName": nome, "shortDisplayName": curto or nome,
                     "abbreviation": nome[:3].upper(),
                     "logos": [{"href": f"https://a.espncdn.com/i/teamlogos/soccer/500/{tid}.png"}]},
            "note": note, "stats": [{"name": k, "value": float(v)} for k, v in stats.items()]}


def resposta_libertadores():
    oitavas = {"color": "#81D6AC", "description": "Classificados para as oitavas de final", "rank": 1}
    playoffs = {"color": "#B2BFD0", "description": "Qualifies for Sudamericana KO Playoffs", "rank": 3}
    return {
        "name": "CONMEBOL Libertadores", "abbreviation": "Lib",
        "season": {"year": 2026, "startDate": "2026-01-01T05:00Z"},
        "children": [
            # A ESPN não garante a ordem das entradas: a posição vem de stats.rank.
            {"name": "Grupo A", "standings": {"entries": [
                entrada(8, "Estudiantes de La Plata", 2, 9, oitavas, "Estudiantes"),
                entrada(819, "Flamengo", 1, 16, oitavas),
                entrada(5, "Independiente Medellín", 3, 7, playoffs, "Ind. Medellín"),
            ]}},
            {"name": "Group G", "standings": {"entries": [
                entrada(2, "Liga de Quito", 1, 12, curto="LDU"),
                entrada(7632, "Atletico Mineiro", 2, 10),
            ]}},
        ],
    }


class RespostaFalsa(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def urlopen_falso(dados, urls=None):
    def abrir(req, timeout=None):
        if urls is not None:
            urls.append(req.full_url)
        return RespostaFalsa(gzip.compress(json.dumps(dados).encode("utf-8")))
    return abrir


def campeonato(codigo="conmebol.libertadores", nome="Libertadores"):
    camp = Campeonato(nome=nome, codigo_api=codigo, fonte_api="espn", ano=2026)
    db.session.add(camp)
    db.session.commit()
    return camp


def test_conversao_para_formato_football_data():
    dados = classificacao_espn.converter_standings(resposta_libertadores())
    assert dados["competition"]["name"] == "CONMEBOL Libertadores"
    assert dados["season"]["startDate"].startswith("2026")
    assert [s["group"] for s in dados["standings"]] == ["Grupo A", "Grupo G"]
    linhas = dados["standings"][0]["table"]
    assert [l["position"] for l in linhas] == [1, 2, 3]
    assert linhas[0] == {
        "position": 1,
        "team": {"id": "espn:819", "name": "Flamengo", "shortName": "Flamengo", "tla": "FLA",
                 "crest": "https://a.espncdn.com/i/teamlogos/soccer/500/819.png"},
        "playedGames": 6, "won": 5, "draw": 1, "lost": 1, "points": 16,
        "goalsFor": 8, "goalsAgainst": 5, "goalDifference": 3,
        "_zona": {"nome": "Classificados para as oitavas de final", "cor": "#81D6AC"},
    }
    assert linhas[2]["_zona"]["nome"] == "Playoffs da Sul-Americana"
    # Nome padronizado igual ao dos jogos.
    assert dados["standings"][1]["table"][1]["team"]["shortName"] == "Atlético-MG"


def test_sem_grupos_vira_standings_vazio():
    dados = classificacao_espn.converter_standings({"name": "Copa do Brasil", "season": {"year": 2026}})
    assert dados["standings"] == [] and dados["season"]["startDate"] == "2026-01-01"


def test_tabela_espn_consulta_e_grava_cache(client, app):
    camp = campeonato()
    urls = []
    with app.test_request_context(), \
            patch.object(classificacao_espn, "urlopen", urlopen_falso(resposta_libertadores(), urls)):
        tabela = dados_tabela(camp)
        # Segunda chamada dentro de 15 min usa o cache, sem nova requisição.
        assert dados_tabela(camp)["fonteCache"]
    assert len(urls) == 1
    assert urls[0].startswith(
        "https://site.api.espn.com/apis/v2/sports/soccer/conmebol.libertadores/standings?season=2026")
    assert tabela["sucesso"] and not tabela["fonteCache"]
    assert tabela["mataMata"] == []
    assert [g_["nome"] for g_ in tabela["grupos"]] == ["Grupo A", "Grupo G"]
    primeira = tabela["grupos"][0]["linhas"][0]
    assert primeira["time"] == "Flamengo" and primeira["pontos"] == 16
    assert primeira["zona"] == {"nome": "Classificados para as oitavas de final", "cor": "#81D6AC",
                                "de": 1, "ate": 1}
    assert "https://a.espncdn.com/i/teamlogos/soccer/500/819.png" in primeira["escudo"]["fontes"]
    assert tabela["legendas"] == [
        {"nome": "Classificados para as oitavas de final", "cor": "#81D6AC", "de": 1, "ate": 2},
        {"nome": "Playoffs da Sul-Americana", "cor": "#B2BFD0", "de": 3, "ate": 3},
    ]
    cache = ClassificacaoCache.query.filter_by(campeonato_id=camp.id).one()
    assert json.loads(cache.dados_json)["_cache_competicao"] == "CONMEBOL.LIBERTADORES"


def test_falha_da_espn_usa_cache_expirado(app):
    camp = campeonato()
    with app.test_request_context(), \
            patch.object(classificacao_espn, "urlopen", urlopen_falso(resposta_libertadores())):
        dados_tabela(camp)
    cache = ClassificacaoCache.query.filter_by(campeonato_id=camp.id).one()
    cache.atualizado_em = datetime.utcnow() - timedelta(minutes=30)
    db.session.commit()

    def falha(*args, **kwargs):
        raise OSError("offline")
    with app.test_request_context(), patch.object(classificacao_espn, "urlopen", falha):
        tabela = dados_tabela(camp)
    assert tabela["sucesso"] and tabela["fonteCache"]
    assert "Não foi possível atualizar agora" in tabela["aviso"]
    assert len(tabela["grupos"]) == 2


def test_falha_da_espn_sem_cache(app):
    camp = campeonato()
    with app.test_request_context(), \
            patch.object(classificacao_espn, "requisitar_standings", side_effect=ErroEspn("offline")):
        tabela = dados_tabela(camp)
    assert not tabela["sucesso"] and "ESPN" in tabela["erro"] and tabela["grupos"] == []


def test_copa_do_brasil_sem_fase_de_grupos(app):
    camp = campeonato("bra.copa_do_brazil", "Copa do Brasil")
    resposta = {"name": "Copa do Brasil", "abbreviation": "CBR", "season": {"year": 2026}}
    with app.test_request_context(), patch.object(classificacao_espn, "urlopen", urlopen_falso(resposta)):
        tabela = dados_tabela(camp)
    assert not tabela["sucesso"]
    assert tabela["erro"] == "Copa do Brasil não tem fase de classificação; os confrontos estão na aba Jogos."
    assert tabela["grupos"] == [] and tabela["mataMata"] == []


def test_escudo_de_time_estrangeiro_vem_do_cache_espn(app):
    camp = campeonato()
    dados = classificacao_espn.converter_standings(resposta_libertadores())
    db.session.add(ClassificacaoCache(campeonato_id=camp.id, dados_json=json.dumps(dados),
                                      atualizado_em=datetime.utcnow()))
    db.session.commit()
    with app.test_request_context():
        g.pop("_escudos_cache", None)
        escudo = escudo_time("Liga de Quito", campeonato_id=camp.id)
        medellin = escudo_time("Independiente Medellín", campeonato_id=camp.id)
    # Escudo local (config_escudos.ESCUDOS_COPAS) vem primeiro; o crest da ESPN fica de reserva.
    assert escudo["fontes"] == ["/static/escudos/liga-de-quito.png",
                                "https://a.espncdn.com/i/teamlogos/soccer/500/2.png"]
    assert medellin["fontes"][-1] == "https://a.espncdn.com/i/teamlogos/soccer/500/5.png"
