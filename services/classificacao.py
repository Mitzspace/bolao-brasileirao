"""
classificacao.py — Serviço para consultar, formatar e armazenar em cache a classificação da API football-data.org.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode, quote

from database import db
from models import Campeonato, ClassificacaoCache
from config_zonas import obter_zona, obter_legendas

BASE_URL = "https://api.football-data.org/v4"
CACHE_EXPIRACAO_MINUTOS = 15

try:
    from zoneinfo import ZoneInfo
    FUSO_SP = ZoneInfo("America/Sao_Paulo")
except Exception:
    FUSO_SP = timezone(timedelta(hours=-3))


def _requisitar_api(token, competicao, temporada=None, recurso="standings"):
    """Executa requisição HTTP para a API football-data.org."""
    if not token:
        raise ValueError("Token da API football-data.org não fornecido.")

    url = f"{BASE_URL}/competitions/{quote(str(competicao), safe='')}/{recurso}"
    if temporada:
        url += "?" + urlencode({"season": temporada})

    req = Request(
        url,
        headers={
            "X-Auth-Token": token,
            "User-Agent": "BolaoApp/2.0",
        },
    )

    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _formatar_horario_brasilia(dt_utc):
    """Converte datetime UTC para string formatada de horário em Brasília (HH:MM de DD/MM)."""
    if not dt_utc:
        return ""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_br = dt_utc.astimezone(FUSO_SP)
    return dt_br.strftime("%H:%M de %d/%m")


def buscar_classificacao(token=None, competicao="BSA", temporada=None, campeonato_id=None, fonte_api=None):
    """
    Busca a classificação de uma competição na API ou no cache do banco de dados.
    fonte_api='espn' consulta a ESPN (services/classificacao_espn.py, sem token); o resto, a football-data.
    
    Retorna um dicionário:
    {
        "sucesso": bool,
        "dados": { ... },
        "grupos": [
            {
                "nome": "Tabela Única" ou "Grupo A",
                "linhas": [
                    {
                        "posicao": 1,
                        "time_id": 123,
                        "time_nome": "Palmeiras",
                        "time_sigla": "PAL",
                        "escudo": "https://...",
                        "pontos": 45,
                        "jogos": 20,
                        "vitorias": 13,
                        "empates": 6,
                        "derrotas": 1,
                        "gols_pro": 35,
                        "gols_contra": 12,
                        "saldo_gols": 23,
                        "forma": "W,W,D,W,L",
                        "zona": { ... }
                    },
                    ...
                ]
            }
        ],
        "legendas": [ ... ],
        "fonte_cache": bool,
        "horario_cache": str, # Ex: "14:30 de 04/10"
        "aviso": str | None,
        "erro": str | None
    }
    """
    espn = fonte_api == "espn"
    token = token or os.environ.get("FOOTBALL_DATA_TOKEN")

    camp = None
    if campeonato_id:
        camp = db.session.get(Campeonato, campeonato_id)
    elif competicao:
        camp = Campeonato.query.filter_by(codigo_api=competicao).first()

    cache_db = camp.classificacao_cache if camp else None
    agora_utc = datetime.now(timezone.utc)

    # 1. Checa se o cache no banco existe e ainda é válido (<= 15 min)
    if cache_db and cache_db.atualizado_em:
        dt_atualizado = cache_db.atualizado_em.replace(tzinfo=timezone.utc)
        if agora_utc - dt_atualizado <= timedelta(minutes=CACHE_EXPIRACAO_MINUTOS):
            try:
                dados_json = json.loads(cache_db.dados_json)
                if not _cache_compativel(dados_json, competicao, temporada):
                    raise ValueError("Cache de outra competição ou temporada")
                return _processar_resposta(
                    dados_json,
                    competicao,
                    fonte_cache=True,
                    horario_cache=_formatar_horario_brasilia(cache_db.atualizado_em),
                )
            except Exception as e:
                print(f"Erro ao ler cache JSON: {e}")

    # 2. Se o cache expirou ou não existe, consulta a API football-data.org
    try:
        aviso = None
        if espn:
            from services.classificacao_espn import buscar_classificacao_espn
            dados_api = buscar_classificacao_espn(competicao, temporada)
        else:
            dados_api = _buscar_football_data(token, competicao, temporada)
        if not espn and dados_api.get("competition", {}).get("type") == "CUP" and "matches" not in dados_api:
            try:
                partidas = _requisitar_api(token, competicao, temporada, recurso="matches")
                dados_api["matches"] = partidas.get("matches", [])
            except (HTTPError, URLError, TimeoutError, ValueError):
                aviso = "A classificação está disponível, mas não foi possível atualizar o mata-mata."
        dados_api["_cache_competicao"] = competicao.upper()
        dados_api["_cache_temporada"] = str(temporada) if temporada else None
        dados_api["_aviso"] = aviso
        
        # Salva ou atualiza no banco
        if camp:
            if not cache_db:
                cache_db = ClassificacaoCache(
                    campeonato_id=camp.id,
                    dados_json=json.dumps(dados_api),
                    atualizado_em=agora_utc.replace(tzinfo=None),
                )
                db.session.add(cache_db)
            else:
                cache_db.dados_json = json.dumps(dados_api)
                cache_db.atualizado_em = agora_utc.replace(tzinfo=None)
            db.session.commit()

        return _processar_resposta(
            dados_api,
            competicao,
            fonte_cache=False,
            horario_cache=_formatar_horario_brasilia(agora_utc),
        )

    except Exception as erro:
        db.session.rollback()
        # 3. Caso de falha na API: se houver cache prévio (mesmo expirado), retorna ele com aviso
        if cache_db and cache_db.dados_json:
            try:
                dados_json = json.loads(cache_db.dados_json)
                if not _cache_compativel(dados_json, competicao, temporada):
                    raise ValueError("Cache de outra competição ou temporada")
                horario_formatado = _formatar_horario_brasilia(cache_db.atualizado_em)
                resultado = _processar_resposta(
                    dados_json,
                    competicao,
                    fonte_cache=True,
                    horario_cache=horario_formatado,
                )
                resultado["aviso"] = f"Não foi possível atualizar agora. Exibindo dados salvos de {horario_formatado}."
                resultado["erro"] = str(erro)
                return resultado
            except Exception:
                pass

        # Sem cache disponível para fallback
        msg_erro = f"Não foi possível carregar a tabela da competição {competicao}."
        if espn:
            msg_erro = "Não foi possível carregar a tabela da ESPN agora. Tente novamente em alguns minutos."
        elif isinstance(erro, HTTPError):
            if erro.code == 429:
                msg_erro = "Limite de requisições da API atingido. Tente novamente em alguns minutos."
            elif erro.code == 403:
                msg_erro = "Token da API inválido ou sem permissão para esta competição."
            elif erro.code == 404:
                msg_erro = f"Competição ou temporada {temporada or ''} não encontrada."
        
        return {
            "sucesso": False,
            "grupos": [],
            "legendas": obter_legendas(competicao),
            "fonte_cache": False,
            "horario_cache": "",
            "aviso": None,
            "erro": msg_erro,
        }


def _buscar_football_data(token, competicao, temporada):
    try:
        return _requisitar_api(token, competicao, temporada)
    except HTTPError as erro:
        if competicao.upper() not in {"CL", "WC", "EC", "CLI", "FAC"} or erro.code != 404:
            raise
        dados_api = _requisitar_api(token, competicao, temporada, recurso="matches")
        dados_api.setdefault("standings", [])
        return dados_api


def _processar_resposta(dados_api, competicao_codigo, fonte_cache=False, horario_cache=""):
    """Normaliza o payload retornado pela API football-data.org para a estrutura de grupos e linhas."""
    standings = dados_api.get("standings", [])
    competition_info = dados_api.get("competition", {})
    season_info = dados_api.get("season", {})

    grupos = []
    # Zonas que vêm da própria API (ESPN: table[]._zona), agregadas para a legenda.
    legendas_api = {}

    for st in standings:
        tipo = st.get("type", "TOTAL")
        # Consideramos apenas a tabela do tipo TOTAL (classificação geral da fase/grupo)
        if tipo != "TOTAL":
            continue

        nome_grupo = st.get("group") or competition_info.get("name") or "Classificação Geral"
        # Melhora exibição do nome do grupo (ex: GROUP_A -> Grupo A)
        if nome_grupo and nome_grupo.startswith("GROUP_"):
            letra = nome_grupo.replace("GROUP_", "")
            nome_grupo = f"Grupo {letra}"

        linhas = []
        for table_row in st.get("table", []):
            pos = table_row.get("position", 0)
            team = table_row.get("team", {})
            
            zona = obter_zona(competicao_codigo, pos, st.get("stage"))
            if table_row.get("_zona"):
                zona = {**table_row["_zona"], "faixa": (pos, pos)}
                atual = legendas_api.setdefault(zona["nome"], {**zona})
                atual["faixa"] = (min(atual["faixa"][0], pos), max(atual["faixa"][1], pos))

            linhas.append({
                "posicao": pos,
                "time_id": team.get("id"),
                "time_nome": nome_time_tabela(team, competicao_codigo),
                "time_nome_completo": team.get("name") or "",
                "time_sigla": team.get("tla") or "",
                "escudo": team.get("crest") or "",
                "pontos": table_row.get("points", 0),
                "jogos": table_row.get("playedGames", 0),
                "vitorias": table_row.get("won", 0),
                "empates": table_row.get("draw", 0),
                "derrotas": table_row.get("lost", 0),
                "gols_pro": table_row.get("goalsFor", 0),
                "gols_contra": table_row.get("goalsAgainst", 0),
                "saldo_gols": table_row.get("goalDifference", 0),
                "forma": table_row.get("form") or "",
                "zona": zona,
            })

        grupos.append({
            "nome": nome_grupo,
            "estagio": st.get("stage"),
            "linhas": linhas,
        })

    return {
        "sucesso": True,
        "competicao_nome": competition_info.get("name", "Campeonato"),
        "temporada": season_info.get("startDate", "")[:4] if season_info.get("startDate") else "",
        "grupos": grupos,
        "legendas": (sorted(legendas_api.values(), key=lambda z: z["faixa"]) if legendas_api
                     else obter_legendas(competicao_codigo, [g["estagio"] for g in grupos])),
        "mata_mata": _processar_mata_mata(dados_api.get("matches", [])),
        "fonte_cache": fonte_cache,
        "horario_cache": horario_cache,
        "aviso": dados_api.get("_aviso"),
        "erro": None,
    }


def _cache_compativel(dados, competicao, temporada):
    codigo = dados.get("_cache_competicao") or dados.get("competition", {}).get("code")
    ano = dados.get("_cache_temporada") or (dados.get("season", {}).get("startDate") or "")[:4]
    return (str(codigo).upper() == competicao.upper()
            and (not temporada or str(ano) == str(temporada)))


ESTAGIOS_MATA_MATA = {
    "PLAYOFFS": "Playoffs", "LAST_64": "32 avos de final",
    "LAST_32": "16 avos de final", "LAST_16": "Oitavas de final",
    "QUARTER_FINALS": "Quartas de final", "SEMI_FINALS": "Semifinais",
    "THIRD_PLACE": "Disputa do terceiro lugar", "FINAL": "Final",
}


def _processar_mata_mata(partidas):
    fases = []
    for estagio, nome in ESTAGIOS_MATA_MATA.items():
        jogos = []
        for partida in sorted(partidas, key=lambda p: (p.get("utcDate") or "", p.get("id") or 0)):
            if partida.get("stage") != estagio:
                continue
            placar = partida.get("score") or {}
            horario = partida.get("utcDate")
            try:
                data = datetime.fromisoformat(horario.replace("Z", "+00:00")) if horario else None
            except ValueError:
                data = None
            jogos.append({
                "id": partida.get("id"),
                "casa": (partida.get("homeTeam") or {}).get("shortName") or (partida.get("homeTeam") or {}).get("name") or "A definir",
                "fora": (partida.get("awayTeam") or {}).get("shortName") or (partida.get("awayTeam") or {}).get("name") or "A definir",
                "gols_casa": (placar.get("fullTime") or {}).get("home"),
                "gols_fora": (placar.get("fullTime") or {}).get("away"),
                "penaltis": placar.get("penalties") or {},
                "status": partida.get("status"),
                "horario": _formatar_horario_brasilia(data),
            })
        if jogos:
            fases.append({"nome": nome, "jogos": jogos})
    return fases


def nome_time_tabela(team, competicao):
    original = team.get("shortName") or team.get("name") or "Time"
    if competicao.upper() != "BSA":
        return original
    from services.sync import _normalizar_time
    nomes = {"athletico pr": "Atlético Paranaense", "atletico mg": "Atlético-MG"}
    return nomes.get(_normalizar_time(team.get("name") or original),
                     nomes.get(_normalizar_time(original), original))
