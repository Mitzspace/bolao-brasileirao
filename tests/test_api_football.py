"""API-Football (api-sports.io) como segundo provedor; sem rede: urlopen é simulado com a
resposta real de /fixtures?league=13&season=2024 (tests/dados_api_football_cli_2024.json)."""
import copy
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from database import db
from models import Campeonato, Jogo, Resultado, Rodada
from services.contexto_bolao import ordem_rodada
from services.importador_api_football import ErroApiFootball, buscar_jogos_api_football, converter_fixtures
from services.importador_jogos import extrair_dados_partida
from services.sync import campeonatos_da_competicao, sync_competicao, sync_jogos
from tests.test_interface import entrar, gestao  # noqa: F401

DADOS = json.loads((Path(__file__).parent / "dados_api_football_cli_2024.json").read_text(encoding="utf-8"))

NOMES_LIBERTADORES = [
    "Rodada 1 · 1ª fase", "Rodada 2 · 2ª fase", "Rodada 3 · 3ª fase",
    *[f"Rodada {3 + n} · Fase de grupos - {n}ª rodada" for n in range(1, 7)],
    "Rodada 10 · Oitavas de final", "Rodada 11 · Quartas de final", "Rodada 12 · Semifinal", "Rodada 13 · Final",
]


class _Resposta:
    def __init__(self, dados):
        self._corpo = json.dumps(dados).encode()

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _api(dados=None):
    """patch de urlopen que devolve 'dados' (padrão: resposta real) e registra as requisições."""
    return patch("services.importador_api_football.urlopen",
                 side_effect=lambda req, timeout=None: _Resposta(DADOS if dados is None else dados))


def _resposta_com(fixtures):
    return {**DADOS, "results": len(fixtures), "response": fixtures}


def _fixture(rodada, casa, fora):
    return copy.deepcopy(next(f for f in DADOS["response"] if f["league"]["round"] == rodada
                              and f["teams"]["home"]["name"] == casa and f["teams"]["away"]["name"] == fora))


def _por_id(jogos):
    return {j["external_id"]: j for j in jogos}


def _campeonato(nome="Libertadores", codigo="13", ano=2024, fonte="api-football", rodada=None):
    c = Campeonato(nome=nome, ano=ano, codigo_api=codigo, fonte_api=fonte)
    db.session.add(c)
    db.session.flush()
    if rodada:
        db.session.add(Rodada(nome=rodada, campeonato_id=c.id))
    db.session.commit()
    return c


def _jogos(camp):
    return Jogo.query.join(Rodada).filter(Rodada.campeonato_id == camp.id).all()


# ---------- Conversão das fixtures ----------

def test_jogo_decidido_nos_penaltis():
    flu = _fixture("Round of 16", "Fluminense", "Gremio")
    item = converter_fixtures(_resposta_com([flu]))[0]
    assert item["external_id"] == str(flu["fixture"]["id"])
    assert (item["status"], item["status_api"], item["finalizado"]) == ("FINISHED", "PEN", True)
    assert (item["gols_casa_real"], item["gols_fora_real"]) == (2, 1)  # goals = jogo normal
    assert (item["penaltis_casa_real"], item["penaltis_fora_real"]) == (4, 2)
    assert (item["estagio"], item["fase"], item["matchday"]) == ("LAST_16", "Oitavas de final", None)
    # -03:00 com timezone=America/Sao_Paulo: o horário local é mantido, sem tzinfo.
    esperado = datetime.fromisoformat(flu["fixture"]["date"]).replace(tzinfo=None)
    assert item["data"] == esperado and item["data"].tzinfo is None


def test_jogo_encerrado_no_tempo_normal():
    jogos = converter_fixtures(DADOS)
    grupo = next(j for j in jogos if j["estagio"] == "GROUP_STAGE")
    assert grupo["finalizado"] and grupo["matchday"] in range(1, 7) and grupo["fase"] == "Fase de grupos"
    assert grupo["penaltis_casa_real"] is None and grupo["pode_penaltis"] is False
    assert len(jogos) == DADOS["results"] == 155
    assert sum(1 for j in jogos if j["penaltis_casa_real"] is not None) == 6


@pytest.mark.parametrize("status", ["1H", "HT", "2H", "ET", "BT", "P", "LIVE", "SUSP", "INT"])
def test_jogo_ao_vivo_nunca_finalizado(status):
    fixture = _fixture("Final", "Atletico-MG", "Botafogo")
    fixture["fixture"]["status"]["short"] = status
    fixture["score"]["penalty"] = {"home": 2, "away": 1}
    item = converter_fixtures(_resposta_com([fixture]))[0]
    assert item["finalizado"] is False
    assert item["gols_casa_real"] is None and item["penaltis_casa_real"] is None  # goals ao vivo é parcial


@pytest.mark.parametrize("status,interno", [("PST", "POSTPONED"), ("NS", "TIMED"), ("TBD", "SCHEDULED"),
                                            ("CANC", "CANCELLED"), ("AWD", "AWARDED"), ("WO", "AWARDED")])
def test_jogo_adiado_ou_sem_placar_definitivo(status, interno):
    fixture = _fixture("Final", "Atletico-MG", "Botafogo")
    fixture["fixture"]["status"]["short"] = status
    if status in ("PST", "NS", "TBD", "CANC"):
        fixture["goals"] = {"home": None, "away": None}
    item = converter_fixtures(_resposta_com([fixture]))[0]
    assert (item["status"], item["finalizado"], item["gols_casa_real"]) == (interno, False, None)


def test_requisicao_usa_urlencode_e_header():
    with _api() as urlopen:
        buscar_jogos_api_football("chave-teste", "13", 2024, data_inicio="2024-08-01", data_fim="2024-08-31")
    req = urlopen.call_args.args[0]
    assert req.full_url == ("https://v3.football.api-sports.io/fixtures?league=13&season=2024"
                            "&timezone=America%2FSao_Paulo&from=2024-08-01&to=2024-08-31")
    assert req.get_header("X-apisports-key") == "chave-teste"


@pytest.mark.parametrize("erros,trecho", [
    ({"plan": "Free plans do not have access to this season, try from 2022 to 2024."}, "try from 2022 to 2024"),
    ({"token": "Error/Missing application key."}, "Chave da API-Football inválida"),
    ({"requests": "You have reached the request limit for the day."}, "Limite diário"),
])
def test_erro_no_corpo_com_http_200(erros, trecho):
    with _api({"get": "fixtures", "errors": erros, "results": 0, "response": []}):
        with pytest.raises(ErroApiFootball) as e:
            buscar_jogos_api_football("chave-teste", "13", 2026)
    assert trecho in str(e.value) and "chave-teste" not in str(e.value)


def test_sem_chave_nao_chama_a_api():
    with _api() as urlopen, pytest.raises(ErroApiFootball, match="API_FOOTBALL_KEY"):
        buscar_jogos_api_football(None, "13", 2024)
    assert urlopen.call_count == 0


# ---------- pode_penaltis ----------

def test_pode_penaltis_ida_volta_e_jogo_unico():
    jogos = converter_fixtures(DADOS)
    for estagio in ("ROUND_1", "ROUND_2", "ROUND_3", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS"):
        fase = [j for j in jogos if j["estagio"] == estagio]
        confrontos = {}
        for j in fase:
            confrontos.setdefault(frozenset((j["time_casa"], j["time_fora"])), []).append(j)
        for par in confrontos.values():
            ida, volta = sorted(par, key=lambda j: j["data"])
            assert (ida["pode_penaltis"], volta["pode_penaltis"]) == (False, True), estagio
    final = [j for j in jogos if j["estagio"] == "FINAL"]
    assert len(final) == 1 and final[0]["pode_penaltis"] is True  # jogo único
    assert not any(j["pode_penaltis"] for j in jogos if j["estagio"] == "GROUP_STAGE")
    # Todo jogo decidido nos pênaltis é um jogo em que pênaltis eram possíveis.
    assert all(j["pode_penaltis"] for j in jogos if j["penaltis_casa_real"] is not None)


def test_import_parcial_so_da_ida_nao_marca_quando_a_volta_ja_existe(app):
    camp = _campeonato()
    ida = _fixture("Round of 16", "Gremio", "Fluminense")
    volta = _fixture("Round of 16", "Fluminense", "Gremio")
    assert ida["fixture"]["timestamp"] < volta["fixture"]["timestamp"]
    with _api(_resposta_com([volta])):
        sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)
    with _api(_resposta_com([ida])):
        sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)
    marcados = {j.external_id: j.pode_penaltis for j in _jogos(camp)}
    assert marcados == {str(volta["fixture"]["id"]): True, str(ida["fixture"]["id"]): False}


def test_sync_nao_desmarca_pode_penaltis_manual(app):
    camp = _campeonato()
    with _api():
        sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)
    grupo = next(j for j in _jogos(camp) if "Fase de grupos" in j.rodada.nome)
    grupo.pode_penaltis = True  # marcado à mão pelo responsável
    db.session.commit()
    with _api():
        sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)
        sync_competicao("k", "13", 2024, fonte_api="api-football")
    assert db.session.get(Jogo, grupo.id).pode_penaltis is True


# ---------- Rodadas ----------

def test_rodadas_da_libertadores_2024_em_ordem(app):
    camp = _campeonato()
    with _api() as urlopen:
        r = sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)
    assert urlopen.call_count == 1
    assert (r["criados"], r["rodadas_criadas"], r["resultados_salvos"]) == (155, 13, 155)
    rodadas = sorted(Rodada.query.filter_by(campeonato_id=camp.id), key=ordem_rodada)
    assert [x.nome for x in rodadas] == NOMES_LIBERTADORES
    assert [len(x.jogos) for x in rodadas] == [6, 16, 8, 16, 16, 16, 16, 16, 16, 16, 8, 4, 1]
    jogos = _jogos(camp)
    assert {j.external_fonte for j in jogos} == {"api-football"}
    flu = next(j for j in jogos if j.time_casa == "Fluminense" and j.time_fora == "Grêmio")
    res = Resultado.query.filter_by(jogo_id=flu.id).one()
    assert (res.gols_casa_real, res.gols_fora_real, res.penaltis_casa_real, res.penaltis_fora_real) == (2, 1, 4, 2)
    assert flu.encerrado and flu.pode_penaltis
    # Nova sincronização não duplica nem renumera.
    with _api():
        assert sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)["criados"] == 0
    assert sorted(x.nome for x in Rodada.query.filter_by(campeonato_id=camp.id)) == sorted(NOMES_LIBERTADORES)


def test_import_parcial_e_fase_sorteada_depois_mantem_numeracao(app):
    camp = _campeonato()
    so_quartas = [f for f in DADOS["response"] if f["league"]["round"] == "Quarter-finals"]
    with _api(_resposta_com(so_quartas)):
        sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)
    assert {r.nome for r in Rodada.query.filter_by(campeonato_id=camp.id)} == {"Rodada 11 · Quartas de final"}
    oitavas_e_quartas = [f for f in DADOS["response"] if f["league"]["round"] in ("Round of 16", "Quarter-finals")]
    with _api(_resposta_com(oitavas_e_quartas)):
        sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)
    nomes = {r.nome: len(r.jogos) for r in Rodada.query.filter_by(campeonato_id=camp.id)}
    assert nomes == {"Rodada 10 · Oitavas de final": 16, "Rodada 11 · Quartas de final": 8}


def test_fase_ja_salva_e_reaproveitada_pelo_rotulo(app):
    camp = _campeonato(rodada="Rodada 99 · Oitavas de final")
    oitavas = [f for f in DADOS["response"] if f["league"]["round"] == "Round of 16"]
    with _api(_resposta_com(oitavas)):
        sync_jogos("k", camp.id, "13", temporada=2024, campeonato_completo=True)
    assert {r.nome: len(r.jogos) for r in Rodada.query.filter_by(campeonato_id=camp.id)} == {
        "Rodada 99 · Oitavas de final": 16}


def test_rodada_por_numero_local(app):
    camp = _campeonato()
    with _api():
        r = sync_jogos("k", camp.id, "13", temporada=2024, rodada_api="10")
    assert r["criados"] == 16
    assert {x.nome for x in Rodada.query.filter_by(campeonato_id=camp.id)} == {"Rodada 10 · Oitavas de final"}


@pytest.mark.parametrize("liga,rodadas,esperado", [
    ("73", ["1st Round", "3rd Round", "Round of 16", "Final"],
     ["Rodada 1 · 1ª fase", "Rodada 3 · 3ª fase", "Rodada 4 · Oitavas de final", "Rodada 7 · Final"]),
    ("11", ["1st Round", "Group Stage - 6", "Knockout Round Play-offs", "Round of 16", "Final"],
     ["Rodada 1 · 1ª fase", "Rodada 7 · Fase de grupos - 6ª rodada", "Rodada 8 · Playoffs",
      "Rodada 9 · Oitavas de final", "Rodada 12 · Final"]),
    ("629", ["Regular Season - 1", "Regular Season - 8", "Semi-finals", "Final"],
     ["Rodada 1", "Rodada 8", "Rodada 9 · Semifinal", "Rodada 10 · Final"]),
    ("71", ["Regular Season - 1", "Regular Season - 38"], ["Rodada 1", "Rodada 38"]),
    ("999", ["Group Stage - 3", "8th Finals", "Final"],
     ["Rodada 3 · Fase de grupos - 3ª rodada", "Rodada 7 · Oitavas de final", "Rodada 11 · Final"]),
])
def test_formatos_das_outras_ligas(liga, rodadas, esperado):
    from services.competicoes import fase_api_football, nomes_rodadas_api_football
    itens = []
    for i, rodada in enumerate(rodadas):
        estagio, numero, fase = fase_api_football(rodada)
        itens.append({"external_id": str(i), "estagio": estagio, "matchday": numero, "fase": fase,
                      "data": datetime(2024, 1, 1 + i)})
    nome = nomes_rodadas_api_football(itens, liga)
    assert [nome(i) for i in itens] == esperado
    assert sorted(esperado, key=lambda n: ordem_rodada(Rodada(nome=n, id=0))) == esperado


# ---------- Sincronização compartilhada ----------

def test_sync_compartilhado_por_fonte_liga_e_ano(app):
    campeonatos = [_campeonato(f"Bolão {i}", rodada="Rodada 13 · Final") for i in range(3)]
    outro_ano = _campeonato("2023", ano=2023, rodada="Rodada 13 · Final")
    outra_fonte = _campeonato("Mesmo código, football-data", fonte="football-data", rodada="Rodada 13 · Final")
    final = _fixture("Final", "Atletico-MG", "Botafogo")
    for camp in campeonatos + [outro_ano, outra_fonte]:
        rodada = Rodada.query.filter_by(campeonato_id=camp.id).one()
        db.session.add(Jogo(time_casa="Atlético-MG", time_fora="Botafogo", rodada_id=rodada.id))
    db.session.commit()
    assert {c.id for c in campeonatos_da_competicao("13", 2024, "api-football")} == {c.id for c in campeonatos}
    with _api() as urlopen:
        resultado = sync_competicao("k", "13", 2024, fonte_api="api-football")
    assert urlopen.call_count == 1
    assert sorted(resultado) == sorted(c.id for c in campeonatos)
    for camp in campeonatos:
        jogo = _jogos(camp)[0]
        assert (jogo.external_fonte, jogo.external_id) == ("api-football", str(final["fixture"]["id"]))
        assert jogo.encerrado and jogo.pode_penaltis
        assert (jogo.resultado.gols_casa_real, jogo.resultado.gols_fora_real) == (1, 3)
    for camp in (outro_ano, outra_fonte):
        assert _jogos(camp)[0].resultado is None and not _jogos(camp)[0].external_id


def test_worker_agrupa_por_fonte_e_pula_provedor_sem_chave(app, monkeypatch, caplog):
    from services import sync_automatico
    sync_automatico._ultima_api_football.clear()
    for nome, codigo, ano, fonte in [("A", "13", 2024, "api-football"), ("B", "13", 2024, "api-football"),
                                     ("C", "11", 2024, "api-football"), ("D", "BSA", 2026, "football-data")]:
        _campeonato(nome, codigo, ano, fonte, rodada="Rodada 1")
    chamadas = []
    monkeypatch.setattr("services.sync_automatico.sync_competicao",
                        lambda chave, codigo, ano, fonte_api=None: chamadas.append((chave, fonte_api, codigo, ano)) or {})
    app.config.update(FOOTBALL_DATA_TOKEN="token-fd", API_FOOTBALL_KEY="chave-af")
    sync_automatico.sincronizar_ciclo(app, agora=0)
    assert chamadas == [("token-fd", None, "BSA", 2026), ("chave-af", "api-football", "11", 2024),
                        ("chave-af", "api-football", "13", 2024)]
    # Cota diária: a mesma liga não é consultada de novo antes do intervalo.
    chamadas.clear()
    sync_automatico.sincronizar_ciclo(app, agora=60)
    assert chamadas == [("token-fd", None, "BSA", 2026)]
    chamadas.clear()
    sync_automatico._ultima_api_football.clear()
    app.config["API_FOOTBALL_KEY"] = None
    with caplog.at_level("WARNING"):
        sync_automatico.sincronizar_ciclo(app, agora=0)
    assert chamadas == [("token-fd", None, "BSA", 2026)]
    assert "API_FOOTBALL_KEY" in caplog.text


# ---------- Rotas ----------

def _admin_no_bolao(client, gestao, fonte="api-football", codigo="13", ano=2024):
    usuario, boloes = gestao
    usuario.admin_global = True
    camp = boloes[0].campeonato
    camp.fonte_api, camp.codigo_api, camp.ano = fonte, codigo, ano
    db.session.commit()
    entrar(client, usuario)
    client.post("/interface/selecionar", data={"bolao_id": boloes[0].id})
    return camp


def test_sincronizacao_manual_usa_chave_do_servidor(client, gestao, app):
    camp = _admin_no_bolao(client, gestao)
    app.config["API_FOOTBALL_KEY"] = "chave-servidor"
    with _api() as urlopen:
        r = client.post("/interface/api/campeonato/sincronizar", json={"acao": "jogos", "campeonatoCompleto": True})
    assert r.status_code == 200, r.get_json()
    assert "155 jogos novos" in r.get_json()["mensagem"]
    assert urlopen.call_args.args[0].get_header("X-apisports-key") == "chave-servidor"
    assert len(_jogos(camp)) == 155


def test_sincronizacao_manual_mostra_erro_de_plano(client, gestao, app):
    _admin_no_bolao(client, gestao, ano=2026)
    app.config["API_FOOTBALL_KEY"] = "chave-servidor"
    erro = {"errors": {"plan": "Free plans do not have access to this season, try from 2022 to 2024."},
            "response": []}
    with _api(erro):
        r = client.post("/interface/api/campeonato/sincronizar", json={"acao": "informacoes"})
    assert r.status_code == 502
    assert "Free plans do not have access to this season" in r.get_json()["erro"]


def test_sincronizacao_manual_sem_chave_api_football(client, gestao, app, monkeypatch):
    _admin_no_bolao(client, gestao)
    app.config["API_FOOTBALL_KEY"] = None
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    r = client.post("/interface/api/campeonato/sincronizar", json={"acao": "jogos", "campeonatoCompleto": True})
    assert r.status_code == 400 and "API_FOOTBALL_KEY" in json.dumps(r.get_json(), ensure_ascii=False)


def test_editar_campeonato_escolhe_fonte(client, gestao):
    camp = _admin_no_bolao(client, gestao, fonte="football-data", codigo="BSA", ano=2026)
    r = client.put("/interface/api/campeonato",
                   json={"nome": "Copa do Brasil", "ano": 2024, "codigoApi": "73", "fonteApi": "api-football"})
    assert r.status_code == 200, r.get_json()
    db.session.refresh(camp)
    assert (camp.fonte_api, camp.codigo_api) == ("api-football", "73")
    assert client.get("/interface/api/campeonato").get_json()["campeonato"]["fonteApi"] == "api-football"
    assert client.put("/interface/api/campeonato",
                      json={"nome": "X", "ano": 2024, "codigoApi": "73", "fonteApi": "outra"}).status_code == 400


# ---------- football-data.org: placar do jogo normal ----------

def _partida_fd(status, score):
    return {"id": 1, "status": status, "stage": "FINAL", "matchday": None, "utcDate": "2025-05-01T19:00:00Z",
            "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"}, "score": score}


def test_football_data_penaltis_usa_regular_mais_prorrogacao():
    item = extrair_dados_partida(_partida_fd("FINISHED", {
        "duration": "PENALTY_SHOOTOUT", "fullTime": {"home": 6, "away": 5},
        "regularTime": {"home": 1, "away": 1}, "extraTime": {"home": 1, "away": 1},
        "penalties": {"home": 4, "away": 3}}))
    assert (item["gols_casa_real"], item["gols_fora_real"]) == (2, 2)
    assert (item["penaltis_casa_real"], item["penaltis_fora_real"]) == (4, 3)
    assert item["finalizado"] and item["data"] == datetime(2025, 5, 1, 16)


def test_football_data_prorrogacao_e_tempo_normal():
    prorrogacao = extrair_dados_partida(_partida_fd("FINISHED", {
        "duration": "EXTRA_TIME", "fullTime": {"home": 2, "away": 1},
        "regularTime": {"home": 1, "away": 1}, "extraTime": {"home": 1, "away": 0}}))
    assert (prorrogacao["gols_casa_real"], prorrogacao["gols_fora_real"], prorrogacao["penaltis_casa_real"]) == (2, 1, None)
    normal = extrair_dados_partida(_partida_fd("FINISHED", {"duration": "REGULAR", "fullTime": {"home": 3, "away": 0}}))
    assert (normal["gols_casa_real"], normal["gols_fora_real"]) == (3, 0)
    # Sem regularTime, desconta a disputa do fullTime.
    sem_regular = extrair_dados_partida(_partida_fd("FINISHED", {
        "duration": "PENALTY_SHOOTOUT", "fullTime": {"home": 5, "away": 4}, "penalties": {"home": 4, "away": 3}}))
    assert (sem_regular["gols_casa_real"], sem_regular["gols_fora_real"]) == (1, 1)


def test_football_data_ao_vivo_nao_finaliza():
    item = extrair_dados_partida(_partida_fd("IN_PLAY", {"duration": "REGULAR", "fullTime": {"home": 1, "away": 0}}))
    assert item["finalizado"] is False


def test_football_data_grava_penaltis_no_resultado(app):
    camp = _campeonato("Copa FD", codigo="CLI", ano=2025, fonte="football-data")
    item = extrair_dados_partida(_partida_fd("FINISHED", {
        "duration": "PENALTY_SHOOTOUT", "fullTime": {"home": 5, "away": 4},
        "regularTime": {"home": 1, "away": 1}, "extraTime": {"home": 0, "away": 0},
        "penalties": {"home": 4, "away": 3}}))
    item["pode_penaltis"] = True
    with patch("services.sync.buscar_jogos_football_data", return_value=[item]) as busca:
        sync_jogos("t", camp.id, "CLI", campeonato_completo=True)
    assert busca.call_count == 1
    jogo = _jogos(camp)[0]
    assert jogo.external_fonte == "football-data.org" and jogo.pode_penaltis
    assert (jogo.resultado.gols_casa_real, jogo.resultado.penaltis_casa_real, jogo.resultado.penaltis_fora_real) == (1, 4, 3)
