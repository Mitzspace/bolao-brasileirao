import json
from datetime import datetime, timedelta
from urllib.error import URLError

from database import db
from models import ClassificacaoCache
from services import classificacao


def payload(codigo="BSA", tipo="LEAGUE", grupo=None):
    return {
        "competition": {"code": codigo, "name": "Competição", "type": tipo},
        "season": {"startDate": "2025-01-01"},
        "standings": [{"type": "TOTAL", "stage": "GROUP_STAGE" if grupo else "REGULAR_SEASON",
                       "group": grupo, "table": [{"position": 1, "team": {"name": "Clube"}, "points": 12}]}],
    }


def test_cache_evita_api(app, campeonato_teste, monkeypatch):
    db.session.add(ClassificacaoCache(campeonato_id=campeonato_teste.id,
                   dados_json=json.dumps(payload()), atualizado_em=datetime.utcnow()))
    db.session.commit()
    def proibido(*args, **kwargs):
        raise AssertionError("Não deve consultar a API com cache válido")
    monkeypatch.setattr(classificacao, "_requisitar_api", proibido)
    resultado = classificacao.buscar_classificacao(temporada=2025, campeonato_id=campeonato_teste.id)
    assert resultado["fonte_cache"]
    assert resultado["grupos"][0]["linhas"][0]["pontos"] == 12


def test_cache_expirado_fallback(app, campeonato_teste, monkeypatch):
    db.session.add(ClassificacaoCache(campeonato_id=campeonato_teste.id,
                   dados_json=json.dumps(payload()), atualizado_em=datetime.utcnow() - timedelta(minutes=16)))
    db.session.commit()
    def falha(*args, **kwargs):
        raise URLError("offline")
    monkeypatch.setattr(classificacao, "_requisitar_api", falha)
    resultado = classificacao.buscar_classificacao(temporada=2025, campeonato_id=campeonato_teste.id)
    assert resultado["sucesso"] and resultado["fonte_cache"] and resultado["aviso"]


def test_cache_outra_temporada_nao_reutilizado(app, campeonato_teste, monkeypatch):
    db.session.add(ClassificacaoCache(campeonato_id=campeonato_teste.id,
                   dados_json=json.dumps(payload()), atualizado_em=datetime.utcnow()))
    db.session.commit()
    chamadas = []
    def buscar(*args, **kwargs):
        chamadas.append(args)
        novo = payload()
        novo["season"]["startDate"] = "2026-01-01"
        return novo
    monkeypatch.setattr(classificacao, "_requisitar_api", buscar)
    resultado = classificacao.buscar_classificacao(temporada=2026, campeonato_id=campeonato_teste.id)
    assert len(chamadas) == 1
    assert resultado["temporada"] == "2026" and not resultado["fonte_cache"]


def test_grupos_champions_sem_zona_da_fase_liga():
    dados = payload("CL", "CUP", "GROUP_A")
    dados["standings"].append({"type": "HOME", "table": []})
    resultado = classificacao._processar_resposta(dados, "CL")
    assert len(resultado["grupos"]) == 1
    assert resultado["grupos"][0]["nome"] == "Grupo A"
    assert resultado["grupos"][0]["linhas"][0]["zona"] is None
    assert resultado["legendas"] == []


def test_copa_carrega_confrontos_e_renderiza(client, campeonato_teste, participante_teste, monkeypatch):
    from tests.test_seletor_bolao import estrutura, login
    estrutura(participante_teste, campeonato_teste, 'Copa')
    campeonato_teste.codigo_api = "WC"
    db.session.commit()
    login(client, participante_teste)
    chamadas = []
    def buscar(token, competicao, temporada=None, recurso="standings"):
        chamadas.append(recurso)
        if recurso == "standings":
            return payload("WC", "CUP", "GROUP_A")
        return {"matches": [{"id": 7, "stage": "FINAL", "utcDate": "2025-07-20T18:00:00Z",
                             "homeTeam": {"name": "Clube A"}, "awayTeam": {"name": "Clube B"},
                             "status": "FINISHED", "score": {"fullTime": {"home": 0, "away": 0}}}]}
    monkeypatch.setattr(classificacao, "_requisitar_api", buscar)
    response = client.get("/tabela")
    assert response.status_code == 200
    assert chamadas == ["standings", "matches"]
    assert "Final" in response.text and "Clube A" in response.text
    assert "15:00 de 20/07" in response.text
    client.get("/tabela")
    assert len(chamadas) == 2


def test_indisponibilidade_sem_cache(client, campeonato_teste, participante_teste, monkeypatch):
    from tests.test_seletor_bolao import estrutura, login
    estrutura(participante_teste, campeonato_teste, 'Amigos')
    login(client, participante_teste)
    def falha(*args, **kwargs):
        raise URLError("offline")
    monkeypatch.setattr(classificacao, "_requisitar_api", falha)
    response = client.get("/tabela")
    assert response.status_code == 200
    assert "Não foi possível carregar" in response.text
