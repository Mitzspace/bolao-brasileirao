"""
classificacao_espn.py — Classificação da API pública (não oficial) da ESPN.

GET https://site.api.espn.com/apis/v2/sports/soccer/{liga}/standings?season=2026&lang=pt&region=br
A resposta é convertida para o MESMO formato da football-data.org (standings[].table[]), para que
services/classificacao.py reaproveite o cache em ClassificacaoCache e services/escudos.py ache o
crest dos times sem mudança no modelo de dados.

children[] = grupos; competição sem children (ex.: Copa do Brasil, só mata-mata) = standings vazio.
A zona de cada linha vem de note{description, color} e é guardada em table[]._zona.
"""
import gzip
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.importador_espn import ErroEspn
from services.sync import nome_padrao

BASE_URL = "https://site.api.espn.com/apis/v2/sports/soccer"
# A ESPN às vezes devolve textos em inglês mesmo com lang=pt.
TRADUCOES_ZONA = {
    "qualifies for sudamericana ko playoffs": "Playoffs da Sul-Americana",
}


def requisitar_standings(liga, temporada):
    liga = str(liga or "").strip().casefold()
    if not re.fullmatch(r"[a-z0-9_]+(?:[.][a-z0-9_]+)+", liga):
        raise ErroEspn("Informe um código de liga ESPN válido.")
    if not re.fullmatch(r"[0-9]{4}", str(temporada or "")):
        raise ErroEspn("Informe a temporada ESPN com quatro dígitos.")
    url = f"{BASE_URL}/{liga}/standings?" + urlencode({"season": temporada, "lang": "pt", "region": "br"})
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    try:
        with urlopen(req, timeout=30) as resposta:
            corpo = resposta.read()
        if corpo[:2] == b"\x1f\x8b":
            corpo = gzip.decompress(corpo)
        dados = json.loads(corpo)
    except (OSError, ValueError, EOFError) as exc:
        raise ErroEspn("Não foi possível consultar a classificação na ESPN.") from exc
    if not isinstance(dados, dict):
        raise ErroEspn("Resposta inválida da ESPN.")
    return dados


def buscar_classificacao_espn(liga, temporada):
    """Consulta a ESPN e devolve o payload já no formato da football-data."""
    return converter_standings(requisitar_standings(liga, temporada))


def _nome_grupo(nome):
    nome = (nome or "").strip()
    return re.sub(r"^group\b", "Grupo", nome, flags=re.IGNORECASE) if nome else None


def _inteiro(valor, padrao=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return padrao


def _zona(note):
    if not isinstance(note, dict) or not (note.get("description") or "").strip():
        return None
    descricao = note["description"].strip()
    cor = (note.get("color") or "").strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", cor):
        cor = "#94a3b8"
    return {"nome": TRADUCOES_ZONA.get(descricao.casefold(), descricao), "cor": cor}


def _linha(entrada, indice):
    time = entrada.get("team") or {}
    stats = {s.get("name"): s.get("value") for s in entrada.get("stats") or [] if isinstance(s, dict)}
    nome = (time.get("displayName") or time.get("name") or time.get("shortDisplayName") or "Time").strip()
    logos = time.get("logos") or []
    crest = (logos[0].get("href") if logos and isinstance(logos[0], dict) else None) or None
    gols_pro, gols_contra = _inteiro(stats.get("pointsFor")), _inteiro(stats.get("pointsAgainst"))
    return {
        "position": _inteiro(stats.get("rank"), indice) or indice,
        # Prefixo evita colisão com ids da football-data em config_escudos.ESCUDOS_POR_API_ID.
        "team": {"id": f"espn:{time['id']}" if time.get("id") else None,
                 "name": nome, "shortName": nome_padrao(nome),
                 "tla": (time.get("abbreviation") or "").strip(), "crest": crest},
        "playedGames": _inteiro(stats.get("gamesPlayed")),
        "won": _inteiro(stats.get("wins")), "draw": _inteiro(stats.get("ties")),
        "lost": _inteiro(stats.get("losses")), "points": _inteiro(stats.get("points")),
        "goalsFor": gols_pro, "goalsAgainst": gols_contra,
        "goalDifference": _inteiro(stats.get("pointDifferential"), gols_pro - gols_contra),
        "_zona": _zona(entrada.get("note")),
    }


def converter_standings(dados):
    """Resposta /standings da ESPN -> {competition, season, standings} no formato da football-data."""
    standings = []
    grupos = [c for c in dados.get("children") or [] if isinstance(c, dict)]
    for numero, grupo in enumerate(grupos, 1):
        entradas = [e for e in (grupo.get("standings") or {}).get("entries") or [] if isinstance(e, dict)]
        tabela = sorted((_linha(e, i) for i, e in enumerate(entradas, 1)),
                        key=lambda l: (l["position"], -l["points"]))
        standings.append({
            "stage": "GROUP_STAGE" if len(grupos) > 1 else "REGULAR_SEASON", "type": "TOTAL",
            "group": _nome_grupo(grupo.get("name") or grupo.get("abbreviation")) or f"Grupo {numero}",
            "table": tabela,
        })
    temporada = dados.get("season") or {}
    return {
        "competition": {"name": dados.get("name") or "", "code": dados.get("abbreviation") or ""},
        "season": {"startDate": temporada.get("startDate")
                   or (f"{temporada['year']}-01-01" if temporada.get("year") else None)},
        "standings": standings,
    }
