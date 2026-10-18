"""
Integração com a API-Football (api-sports.io v3), segundo provedor de jogos e resultados.
Documentação: https://www.api-football.com/documentation-v3

Produz os mesmos dicts internos de services/importador_jogos.py (football-data.org), com
pênaltis, pode_penaltis e o rótulo da fase. Uma requisição traz a temporada inteira da liga
(GET /fixtures?league=13&season=2024&timezone=America/Sao_Paulo).
"""

import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.competicoes import fase_api_football, marcar_pode_penaltis
from services.importador_jogos import _parse_data_brasilia

BASE_URL = "https://v3.football.api-sports.io"
FUSO = "America/Sao_Paulo"

# Placar definitivo. AWD (vitória administrativa) e WO não contam: o placar é de tribunal
# (ou nem houve jogo) e o responsável decide à mão como lançar no bolão.
STATUS_FINALIZADO = {"FT", "AET", "PEN"}
STATUS_AO_VIVO = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "SUSP", "INT"}
# Vocabulário da football-data.org, usado no resto do sistema.
STATUS_INTERNO = {
    "TBD": "SCHEDULED", "NS": "TIMED",
    "1H": "IN_PLAY", "2H": "IN_PLAY", "ET": "IN_PLAY", "P": "IN_PLAY", "LIVE": "IN_PLAY",
    "HT": "PAUSED", "BT": "PAUSED",
    "SUSP": "SUSPENDED", "INT": "SUSPENDED",
    "FT": "FINISHED", "AET": "FINISHED", "PEN": "FINISHED",
    "PST": "POSTPONED", "CANC": "CANCELLED", "ABD": "CANCELLED", "AWD": "AWARDED", "WO": "AWARDED",
}


class ErroApiFootball(Exception):
    """Erro informado pela API no campo 'errors' (mesmo com HTTP 200); mensagem pronta para o usuário."""


def _mensagem_erro(erros):
    if isinstance(erros, dict):
        partes = [f"{chave}: {valor}" if chave not in ("plan", "token", "requests") else str(valor)
                  for chave, valor in erros.items()]
        if "token" in erros:
            partes.insert(0, "Chave da API-Football inválida ou ausente.")
        if "requests" in erros:
            partes.insert(0, "Limite diário de requisições da API-Football atingido.")
        if "plan" in erros:
            partes.insert(0, "Plano da API-Football não permite esta consulta.")
    else:
        partes = [str(e) for e in erros]
    return "API-Football: " + " ".join(partes)


def _requisitar(chave, caminho, params=None):
    if not chave:
        raise ErroApiFootball("Configure API_FOOTBALL_KEY para sincronizar com a API-Football.")
    url = BASE_URL + caminho
    params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    if params:
        url += "?" + urlencode(params)
    req = Request(url, headers={"x-apisports-key": chave})
    with urlopen(req, timeout=20) as resposta:
        dados = json.loads(resposta.read())
    erros = dados.get("errors")
    if erros:  # [] em sucesso; objeto (ou lista preenchida) em erro
        raise ErroApiFootball(_mensagem_erro(erros))
    return dados


def extrair_dados_fixture(item):
    """Converte um item de /fixtures no dict interno (sem pode_penaltis, que depende da fase)."""
    fixture = item.get("fixture") or {}
    teams = item.get("teams") or {}
    goals = item.get("goals") or {}
    penalty = (item.get("score") or {}).get("penalty") or {}
    status_api = ((fixture.get("status") or {}).get("short") or "").upper()
    finalizado = status_api in STATUS_FINALIZADO
    # Ao vivo 'goals' já vem preenchido: só grava placar de jogo encerrado.
    gols_casa, gols_fora = (goals.get("home"), goals.get("away")) if finalizado else (None, None)
    pen_casa, pen_fora = (penalty.get("home"), penalty.get("away")) if finalizado else (None, None)
    if pen_casa is None or pen_fora is None:
        pen_casa = pen_fora = None
    estagio, numero, fase = fase_api_football((item.get("league") or {}).get("round"))
    return {
        "external_id": str(fixture["id"]),
        "matchday": numero,
        "estagio": estagio,
        "fase": fase,
        "time_casa": (teams.get("home") or {}).get("name") or "Casa",
        "time_fora": (teams.get("away") or {}).get("name") or "Fora",
        "data": _parse_data_brasilia(fixture.get("date")),
        "status": STATUS_INTERNO.get(status_api, status_api or None),
        "status_api": status_api or None,
        "finalizado": finalizado,
        "gols_casa_real": int(gols_casa) if gols_casa is not None else None,
        "gols_fora_real": int(gols_fora) if gols_fora is not None else None,
        "penaltis_casa_real": int(pen_casa) if pen_casa is not None else None,
        "penaltis_fora_real": int(pen_fora) if pen_fora is not None else None,
    }


def converter_fixtures(dados):
    """Lista de dicts internos a partir da resposta de /fixtures, com pode_penaltis calculado."""
    jogos = [extrair_dados_fixture(item) for item in dados.get("response") or []]
    marcar_pode_penaltis(jogos)
    return jogos


def _data_iso(valor):
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    return valor


def buscar_jogos_api_football(chave, liga, temporada=None, rodada=None, data_inicio=None, data_fim=None):
    """Todos os jogos da liga/temporada (uma requisição). 'rodada' é o league.round exato da API
    (ex.: 'Round of 16'); o número da rodada local é filtrado em services/sync.py.

    O filtro por datas só é aceito pela API com from e to juntos; sem um deles, busca tudo.
    """
    params = {"league": str(liga).strip(), "season": temporada, "timezone": FUSO}
    if rodada and not str(rodada).isdigit():
        params["round"] = rodada
    if data_inicio and data_fim:
        params["from"], params["to"] = _data_iso(data_inicio), _data_iso(data_fim)
    return converter_fixtures(_requisitar(chave, "/fixtures", params))


def buscar_resultados_api_football(chave, liga, temporada=None, rodada=None, data_inicio=None, data_fim=None):
    return [{k: j[k] for k in ("external_id", "gols_casa_real", "gols_fora_real", "penaltis_casa_real",
                               "penaltis_fora_real", "data")}
            for j in buscar_jogos_api_football(chave, liga, temporada, rodada, data_inicio, data_fim)
            if j["finalizado"] and j["gols_casa_real"] is not None and j["gols_fora_real"] is not None]
