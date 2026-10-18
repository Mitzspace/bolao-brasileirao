"""
Integração com football-data.org.
Documentação: https://www.football-data.org/documentation/quickstart
"""

import json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None


BASE_URL = "https://api.football-data.org/v4"


def _requisitar(token, caminho, params=None):
    url = BASE_URL + caminho

    if params:
        pares = urlencode({k: v for k, v in params.items() if v is not None and v != ""})
        if pares:
            url += "?" + pares

    req = Request(url, headers={"X-Auth-Token": token})

    with urlopen(req, timeout=20) as resposta:
        return json.loads(resposta.read())


def _parse_data_brasilia(data_utc):
    """Converte string UTC da API (ex: 2025-04-12T19:00:00Z) para horário de São Paulo/Brasília."""
    if not data_utc:
        return None
    try:
        dt = datetime.fromisoformat(data_utc.replace("Z", "+00:00"))
        try:
            fuso_brasilia = ZoneInfo("America/Sao_Paulo")
        except Exception:
            fuso_brasilia = timezone(timedelta(hours=-3))
        dt_br = dt.astimezone(fuso_brasilia)
        return dt_br.replace(tzinfo=None)
    except Exception as e:
        print(f"Erro ao converter data '{data_utc}': {e}")
        return None


def _soma_placar(*partes):
    """Soma placares {'home','away'}; None se a primeira parte não tiver os dois lados."""
    if not partes or partes[0].get("home") is None or partes[0].get("away") is None:
        return None, None
    casa = sum(p.get("home") or 0 for p in partes)
    fora = sum(p.get("away") or 0 for p in partes)
    return casa, fora


def placar_jogo_normal(score):
    """(gols casa, gols fora, pênaltis casa, pênaltis fora) do jogo normal (tempo normal + prorrogação).

    Na football-data.org o fullTime de jogo decidido nos pênaltis inclui os gols da disputa
    (https://docs.football-data.org/general/v4/overtime.html); por isso, quando score.duration
    não é REGULAR, o placar é regularTime + extraTime e score.penalties fica separado.
    """
    score = score or {}
    fulltime = score.get("fullTime") or {}
    penaltis = score.get("penalties") or {}
    pen_casa, pen_fora = penaltis.get("home"), penaltis.get("away")
    if pen_casa is None or pen_fora is None:
        pen_casa = pen_fora = None
    duracao = score.get("duration") or "REGULAR"
    if duracao == "REGULAR":
        return fulltime.get("home"), fulltime.get("away"), pen_casa, pen_fora
    regular = score.get("regularTime") or {}
    if regular.get("home") is not None and regular.get("away") is not None:
        casa, fora = _soma_placar(regular, score.get("extraTime") or {})
    elif pen_casa is not None and fulltime.get("home") is not None and fulltime.get("away") is not None:
        casa, fora = fulltime["home"] - pen_casa, fulltime["away"] - pen_fora
    else:
        casa, fora = fulltime.get("home"), fulltime.get("away")
    return casa, fora, pen_casa, pen_fora


# Ao vivo o fullTime já vem preenchido: placar parcial não encerra o jogo.
STATUS_NAO_FINALIZADO = {"SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "EXTRA_TIME", "PENALTY_SHOOTOUT",
                         "SUSPENDED", "POSTPONED", "CANCELLED", "LIVE"}


def extrair_dados_partida(partida):
    """Extrai informações completas de uma partida retornada pela API."""
    gols_casa, gols_fora, pen_casa, pen_fora = placar_jogo_normal(partida.get("score"))
    status = partida.get("status")

    # Jogo finalizado se status for FINISHED ou se houver placar definitivo fora de jogo em andamento
    finalizado = (status == "FINISHED") or (
        status not in STATUS_NAO_FINALIZADO and gols_casa is not None and gols_fora is not None)

    return {
        "external_id": str(partida["id"]),
        "matchday": partida.get("matchday"),
        "estagio": partida.get("stage"),
        "time_casa": partida.get("homeTeam", {}).get("name", "Casa"),
        "time_fora": partida.get("awayTeam", {}).get("name", "Fora"),
        "data": _parse_data_brasilia(partida.get("utcDate")),
        "status": status,
        "finalizado": finalizado,
        "gols_casa_real": int(gols_casa) if gols_casa is not None else None,
        "gols_fora_real": int(gols_fora) if gols_fora is not None else None,
        "penaltis_casa_real": int(pen_casa) if pen_casa is not None and finalizado else None,
        "penaltis_fora_real": int(pen_fora) if pen_fora is not None and finalizado else None,
    }


def buscar_jogos_football_data(
    token, competicao, temporada=None, rodada=None, data_inicio=None, data_fim=None
):
    params = {}

    if temporada:
        params["season"] = temporada
    if rodada:
        params["matchday"] = rodada
    if data_inicio:
        params["dateFrom"] = data_inicio
    if data_fim:
        params["dateTo"] = data_fim

    dados = _requisitar(token, f"/competitions/{competicao}/matches", params)

    from services.competicoes import marcar_pode_penaltis
    return marcar_pode_penaltis([extrair_dados_partida(partida) for partida in dados.get("matches", [])])


def buscar_resultados_football_data(
    token, competicao, temporada=None, rodada=None, data_inicio=None, data_fim=None
):
    params = {"status": "FINISHED"}

    if temporada:
        params["season"] = temporada
    if rodada:
        params["matchday"] = rodada
    if data_inicio:
        params["dateFrom"] = data_inicio
    if data_fim:
        params["dateTo"] = data_fim

    dados = _requisitar(token, f"/competitions/{competicao}/matches", params)

    resultados = []
    for partida in dados.get("matches", []):
        info = extrair_dados_partida(partida)
        if info["gols_casa_real"] is not None and info["gols_fora_real"] is not None:
            resultados.append({
                "external_id": info["external_id"],
                "gols_casa_real": info["gols_casa_real"],
                "gols_fora_real": info["gols_fora_real"],
                "penaltis_casa_real": info["penaltis_casa_real"],
                "penaltis_fora_real": info["penaltis_fora_real"],
                "data": info["data"],
            })

    return resultados
