"""
Integração com football-data.org.
Documentação: https://www.football-data.org/documentation/quickstart
"""

import json
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None


BASE_URL = "https://api.football-data.org/v4"


def _requisitar(token, caminho, params=None):
    url = BASE_URL + caminho

    if params:
        pares = "&".join(f"{k}={v}" for k, v in params.items() if v is not None and v != "")
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


def extrair_dados_partida(partida):
    """Extrai informações completas de uma partida retornada pela API."""
    score = partida.get("score") or {}
    fulltime = score.get("fullTime") or {}

    gols_casa = fulltime.get("home")
    gols_fora = fulltime.get("away")
    status = partida.get("status")

    # Jogo finalizado se status for FINISHED ou se houver placar definitivo
    finalizado = (status == "FINISHED") or (gols_casa is not None and gols_fora is not None)

    return {
        "external_id": str(partida["id"]),
        "matchday": partida.get("matchday"),
        "time_casa": partida.get("homeTeam", {}).get("name", "Casa"),
        "time_fora": partida.get("awayTeam", {}).get("name", "Fora"),
        "data": _parse_data_brasilia(partida.get("utcDate")),
        "status": status,
        "finalizado": finalizado,
        "gols_casa_real": int(gols_casa) if gols_casa is not None else None,
        "gols_fora_real": int(gols_fora) if gols_fora is not None else None,
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

    jogos = []
    for partida in dados.get("matches", []):
        jogos.append(extrair_dados_partida(partida))

    return jogos


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
                "data": info["data"],
            })

    return resultados
