"""Conversor ESPN → dict interno (sem rede)."""
from datetime import datetime

from services.competicoes import nomeador_rodadas
from services.importador_espn import converter_eventos


def _evento(eid, slug, data, casa, fora, score_casa, score_fora, *, completed=True, state="post",
            status="STATUS_FULL_TIME", shootout=None, group=None):
    casa_c = {"homeAway": "home", "score": str(score_casa), "team": {"displayName": casa}}
    fora_c = {"homeAway": "away", "score": str(score_fora), "team": {"displayName": fora}}
    if shootout is not None:
        casa_c["shootoutScore"], fora_c["shootoutScore"] = shootout
    return {
        "id": eid, "date": data, "season": {"slug": slug},
        "status": {"type": {"completed": completed, "state": state, "name": status}},
        "competitions": [{"competitors": [casa_c, fora_c],
                          "group": {"abbreviation": group} if group else {}}],
    }


def test_converte_grupos_mata_mata_e_penaltis():
    dados = {"events": [
        _evento("1", "group-stage", "2025-04-02T00:00:00Z", "A", "B", 1, 0, group="Group A"),
        _evento("2", "group-stage", "2025-04-09T00:00:00Z", "A", "C", 2, 2, group="Group A"),
        _evento("3", "round-of-16", "2025-08-12T22:00:00Z", "A", "D", 0, 0),
        _evento("4", "round-of-16", "2025-08-19T22:00:00Z", "D", "A", 0, 0,
                status="STATUS_FINAL_PEN", shootout=(3, 4)),
        _evento("5", "finals", "2025-11-10T21:00:00Z", "A", "E", 1, 0),
        _evento("6", "trofeu-inconfidencia---finals", "2025-03-15T19:00:00Z", "X", "Y", 1, 1),
    ]}
    jogos = converter_eventos(dados)
    assert [j["external_id"] for j in jogos] == ["1", "2", "3", "4", "5"]
    assert jogos[0]["estagio"] == "GROUP_STAGE" and jogos[0]["matchday"] == 1
    assert jogos[1]["matchday"] == 2
    assert jogos[2]["fase"] == "Oitavas de final" and jogos[2]["pode_penaltis"] is False
    assert jogos[3]["penaltis_casa_real"] == 3 and jogos[3]["penaltis_fora_real"] == 4
    assert jogos[3]["pode_penaltis"] is True
    assert jogos[4]["estagio"] == "FINAL" and jogos[4]["data"] == datetime(2025, 11, 10, 18)
    assert not any(j["finalizado"] is False for j in jogos if j["status"] == "FINISHED")


def test_ao_vivo_nao_finaliza():
    dados = {"events": [
        _evento("9", "semifinals", "2025-10-01T00:00:00Z", "A", "B", 1, 0,
                completed=False, state="in", status="STATUS_SECOND_HALF"),
    ]}
    jogo = converter_eventos(dados)[0]
    assert not jogo["finalizado"] and jogo["gols_casa_real"] is None and jogo["status"] == "IN_PLAY"


def test_nomeador_libertadores_espn():
    itens = [
        {"estagio": "ROUND_1", "fase": "1ª fase", "matchday": None, "external_id": "1", "data": None},
        {"estagio": "GROUP_STAGE", "fase": "Fase de grupos", "matchday": 1, "external_id": "2", "data": None},
        {"estagio": "LAST_16", "fase": "Oitavas de final", "matchday": None, "external_id": "3", "data": None},
        {"estagio": "FINAL", "fase": "Final", "matchday": None, "external_id": "4", "data": None},
    ]
    nome = nomeador_rodadas("espn", itens, "conmebol.libertadores")
    assert nome(itens[0]) == "Rodada 1 · 1ª fase"
    assert nome(itens[1]) == "Rodada 4 · Fase de grupos - 1ª rodada"
    assert nome(itens[2]) == "Rodada 10 · Oitavas de final"
    assert nome(itens[3]) == "Rodada 13 · Final"


def test_mineiro_playoffs_finals():
    dados = {"events": [
        _evento("1", "regular-season", "2025-01-20T00:00:00Z", "A", "B", 1, 0),
        _evento("2", "playoffs---semifinals", "2025-02-15T00:00:00Z", "A", "C", 2, 0),
        _evento("3", "playoffs---finals", "2025-03-15T00:00:00Z", "A", "D", 1, 0),
    ]}
    jogos = converter_eventos(dados)
    assert [j["estagio"] for j in jogos] == ["REGULAR_SEASON", "SEMI_FINALS", "FINAL"]
    nome = nomeador_rodadas("espn", jogos, "bra.camp.mineiro")
    assert nome(jogos[0]) == "Rodada 1"
    assert nome(jogos[1]) == "Rodada 9 · Semifinal"
    assert nome(jogos[2]) == "Rodada 10 · Final"

import gzip
import json
from datetime import date
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import pytest
from services import importador_espn as espn


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    def bloqueada(*args, **kwargs):
        pytest.fail("Teste tentou acessar a rede")
    monkeypatch.setattr(espn, "urlopen", bloqueada)


def evento_padrao(**kwargs):
    return _evento("10", "finals", "2025-04-02T01:00Z", "A", "B", 1, 1, **kwargs)


@pytest.mark.parametrize("status,esperado", [
    ("STATUS_POSTPONED", "POSTPONED"), ("STATUS_CANCELED", "CANCELLED"),
    ("STATUS_CANCELLED", "CANCELLED"), ("STATUS_ABANDONED", "CANCELLED"),
    ("STATUS_SUSPENDED", "SUSPENDED"), ("STATUS_DELAYED", "SUSPENDED"),
    ("STATUS_HALFTIME", "PAUSED"), ("STATUS_AWARDED", "AWARDED"),
])
def test_estados_nao_encerrados_mesmo_com_flag_completed(status, esperado):
    jogo = converter_eventos({"events": [evento_padrao(status=status, shootout=(4, 3))]})[0]
    assert jogo["status"] == esperado
    assert jogo["finalizado"] is False
    assert all(jogo[k] is None for k in (
        "gols_casa_real", "gols_fora_real", "penaltis_casa_real", "penaltis_fora_real"))


@pytest.mark.parametrize("status", sorted(espn.STATUS_FINAIS))
def test_encerramento_confirmado(status):
    jogo = converter_eventos({"events": [evento_padrao(status=status)]})[0]
    assert jogo["status"] == "FINISHED"
    assert jogo["gols_casa_real"] == jogo["gols_fora_real"] == 1


@pytest.mark.parametrize("valor", [None, "", "-1", "1.5", "NaN", True, {}, "abc"])
def test_resultado_incompleto_ou_invalido_nao_e_exportado(monkeypatch, valor):
    ev = evento_padrao()
    ev["competitions"][0]["competitors"][0]["score"] = valor
    monkeypatch.setattr(espn, "_requisitar", lambda *args: {"events": [ev]})
    assert espn.buscar_resultados_espn("bra.1", 2025) == []


def test_penaltis_separados_e_par_incompleto():
    ev = evento_padrao(status="STATUS_FINAL_PEN", shootout=("5", "4"))
    jogo = converter_eventos({"events": [ev]})[0]
    assert (jogo["gols_casa_real"], jogo["penaltis_casa_real"]) == (1, 5)
    ev["competitions"][0]["competitors"][1]["shootoutScore"] = None
    jogo = converter_eventos({"events": [ev]})[0]
    assert jogo["penaltis_casa_real"] is jogo["penaltis_fora_real"] is None


@pytest.mark.parametrize("data,esperado", [
    ("2025-04-02T01:00Z", datetime(2025, 4, 1, 22)),
    ("2025-04-02T01:00:00Z", datetime(2025, 4, 1, 22)),
    ("2025-04-02T01:00:00+02:00", datetime(2025, 4, 1, 20)),
    (None, None),
])
def test_datas_com_fuso(data, esperado):
    ev = evento_padrao()
    ev["date"] = data
    assert converter_eventos({"events": [ev]})[0]["data"] == esperado


@pytest.mark.parametrize("dados", [None, [], {}, {"events": None}, {"events": {}},
    {"events": [None]}, {"events": [{}]}, {"events": [], "error": "unknown league"}])
def test_resposta_invalida(dados):
    with pytest.raises(espn.ErroEspn):
        converter_eventos(dados)


def test_lista_vazia_valida():
    assert converter_eventos({"events": []}) == []


@pytest.mark.parametrize("campo", ["id", "competitors", "date", "team"])
def test_evento_invalido_nao_importa_parcialmente(campo):
    ev = evento_padrao()
    if campo == "id":
        ev.pop("id")
    elif campo == "competitors":
        ev["competitions"][0]["competitors"].pop()
    elif campo == "team":
        ev["competitions"][0]["competitors"][0]["team"] = {}
    else:
        ev["date"] = "2025-04-02T01:00:00"  # sem fuso
    with pytest.raises(espn.ErroEspn):
        converter_eventos({"events": [ev]})


def test_status_e_data_da_competicao_tem_prioridade():
    ev = evento_padrao()
    ev["competitions"][0].update(status={"type": {
        "name": "STATUS_POSTPONED", "state": "pre", "completed": False}}, date="2025-06-01T20:00Z")
    jogo = converter_eventos({"events": [ev]})[0]
    assert jogo["status"] == "POSTPONED"
    assert jogo["data"] == datetime(2025, 6, 1, 17)


@pytest.mark.parametrize("slug,estagio", [("group-stage", "GROUP_STAGE"), ("regular-season", "REGULAR_SEASON")])
def test_rodada_inferida_pela_data_e_nao_pela_ordem_da_resposta(slug, estagio):
    eventos = [_evento("1", slug, "2025-09-01T20:00Z", "A", "B", 0, 0),
               _evento("2", slug, "2025-04-01T20:00Z", "A", "C", 1, 0)]
    for lista, esperado in ((eventos, {"1": 2, "2": 1}), (list(reversed(eventos)), {"1": 2, "2": 1}),
                            (eventos[:1], {"1": 1})):
        jogos = converter_eventos({"events": lista})
        assert all(j["estagio"] == estagio for j in jogos)
        assert {j["external_id"]: j["matchday"] for j in jogos} == esperado
        assert not any(j["pode_penaltis"] for j in jogos)


def _tabela(slug, rodadas, adiados=None):
    """Eventos de `rodadas` (lista de listas de (casa, fora)), uma semana por rodada.
    adiados: {(casa, fora): dias depois do início da tabela} sobrescreve a data do jogo."""
    from datetime import timedelta
    adiados = adiados or {}
    inicio, eventos = datetime(2025, 4, 1, 20), []
    for numero, jogos in enumerate(rodadas, 1):
        for casa, fora in jogos:
            dias = adiados.get((casa, fora), (numero - 1) * 7)
            data = (inicio + timedelta(days=dias)).strftime("%Y-%m-%dT%H:%MZ")
            eventos.append(_evento(f"{numero}{casa}{fora}", slug, data, casa, fora, 0, 0))
    return eventos


TURNO_E_RETURNO = [[("A", "C"), ("B", "D")], [("A", "D"), ("B", "C")], [("A", "B"), ("C", "D")],
                   [("C", "A"), ("D", "B")], [("D", "A"), ("C", "B")], [("B", "A"), ("D", "C")]]


def _rodada_de(jogos):
    return {(j["time_casa"], j["time_fora"]): j["matchday"] for j in jogos}


def test_rodadas_de_grupo_sem_adiamento():
    jogos = converter_eventos({"events": _tabela("group-stage", TURNO_E_RETURNO)})
    esperado = {par: n for n, rodada in enumerate(TURNO_E_RETURNO, 1) for par in rodada}
    assert _rodada_de(jogos) == esperado
    nome = nomeador_rodadas("espn", jogos, "conmebol.libertadores", [])
    assert {nome(j) for j in jogos} == {f"Rodada {3 + n} · Fase de grupos - {n}ª rodada" for n in range(1, 7)}


def test_rodadas_de_grupo_com_adiamento_reparado():
    # A x B da 3ª rodada foi jogado depois da 4ª (e antes da 5ª).
    jogos = converter_eventos({"events": _tabela("group-stage", TURNO_E_RETURNO, {("A", "B"): 24})})
    esperado = {par: n for n, rodada in enumerate(TURNO_E_RETURNO, 1) for par in rodada}
    assert _rodada_de(jogos) == esperado


def test_rodadas_inconsistentes_ficam_sem_matchday():
    # B e C jogam duas vezes entre si: a tabela precisa de mais rodadas que jogos por time.
    rodadas = [[("A", "B")], [("A", "C")], [("B", "C")], [("C", "B")]]
    jogos = converter_eventos({"events": _tabela("group-stage", rodadas)})
    assert all(j["matchday"] is None for j in jogos)
    nome = nomeador_rodadas("espn", jogos, "conmebol.libertadores", [])
    assert {nome(j) for j in jogos} == {"Rodada 4 · Fase de grupos"}


def test_mineiro_rodadas_inferidas_e_nomes():
    rodadas = [[("A", "B"), ("C", "D")], [("A", "C"), ("B", "D")], [("A", "D"), ("B", "C")]]
    eventos = _tabela("regular-season", rodadas) + [
        _evento("s1", "playoffs---semifinals", "2025-05-01T20:00Z", "A", "D", 1, 0),
        _evento("f1", "playoffs---finals", "2025-05-10T20:00Z", "A", "B", 1, 0)]
    jogos = converter_eventos({"events": eventos})
    nome = nomeador_rodadas("espn", jogos, "bra.camp.mineiro", [])
    assert {j["external_id"]: nome(j) for j in jogos} == {
        "1AB": "Rodada 1", "1CD": "Rodada 1", "2AC": "Rodada 2", "2BD": "Rodada 2",
        "3AD": "Rodada 3", "3BC": "Rodada 3", "s1": "Rodada 9 · Semifinal", "f1": "Rodada 10 · Final"}


def test_fase_desconhecida_nao_vira_liga():
    ev = evento_padrao()
    ev["season"]["slug"] = "special-cup"
    jogo = converter_eventos({"events": [ev]})[0]
    assert (jogo["estagio"], jogo["fase"], jogo["matchday"]) == ("OUTRA", "special-cup", None)


@pytest.mark.parametrize("inicio,fim,ids", [
    ("2025-04-01", "2025-04-01", ["1"]),
    (date(2025, 4, 2), None, ["2"]),
    (None, datetime(2025, 4, 1), ["1"]),
    (None, None, ["1", "2", "3"]),
])
def test_filtros_inclusivos_brasilia_e_resultados(monkeypatch, inicio, fim, ids):
    eventos = [_evento("1", "finals", "2025-04-02T01:00Z", "A", "B", 1, 1),
               _evento("2", "finals", "2025-04-03T01:00Z", "B", "A", 0, 0),
               _evento("3", "finals", None, "C", "D", 1, 0)]
    monkeypatch.setattr(espn, "_requisitar", lambda *args: {"events": eventos})
    jogos = espn.buscar_jogos_espn("bra.1", 2025, data_inicio=inicio, data_fim=fim)
    assert [j["external_id"] for j in jogos] == ids
    if "1" in ids:
        assert jogos[0]["pode_penaltis"] is False  # calculado antes do recorte
    resultados = espn.buscar_resultados_espn("bra.1", 2025, data_inicio=inicio, data_fim=fim)
    assert [j["external_id"] for j in resultados] == ids


@pytest.mark.parametrize("inicio,fim", [("invalida", None), ("2025-04-02", "2025-04-01")])
def test_filtro_invalido_falha_antes_da_rede(inicio, fim):
    with pytest.raises(espn.ErroEspn):
        espn.buscar_jogos_espn("bra.1", 2025, data_inicio=inicio, data_fim=fim)


@pytest.mark.parametrize("comprimido", [False, True])
def test_http_json_gzip_e_parametros(monkeypatch, comprimido):
    corpo = json.dumps({"events": []}).encode()
    def resposta(req, timeout):
        url = urlparse(req.full_url)
        assert url.path.endswith("/conmebol.libertadores/scoreboard")
        assert parse_qs(url.query)["dates"] == ["2025"]
        assert timeout == 60
        return BytesIO(gzip.compress(corpo) if comprimido else corpo)
    monkeypatch.setattr(espn, "urlopen", resposta)
    assert espn.buscar_jogos_espn(" CONMEBOL.LIBERTADORES ", 2025) == []


@pytest.mark.parametrize("corpo", [b"", b"<html>erro</html>", b"\x1f\x8bcorrompido"])
def test_corpo_http_invalido(monkeypatch, corpo):
    monkeypatch.setattr(espn, "urlopen", lambda *args, **kwargs: BytesIO(corpo))
    with pytest.raises(espn.ErroEspn):
        espn.buscar_jogos_espn("bra.1", 2025)


@pytest.mark.parametrize("liga,ano", [("", 2025), ("../bra.1", 2025), ("bra.1", None), ("bra.1", "2025x")])
def test_parametros_invalidos_antes_da_rede(liga, ano):
    with pytest.raises(espn.ErroEspn):
        espn.buscar_jogos_espn(liga, ano)
