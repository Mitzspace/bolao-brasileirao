"""
Provedor ESPN (API pública e NÃO oficial, sem chave): site.api.espn.com.
Uma requisição traz a temporada inteira: /apis/site/v2/sports/soccer/{liga}/scoreboard?dates=2026&limit=1000

Produz os mesmos dicts internos da API-Football (services/importador_api_football.py): a fase da
ESPN (season.slug) é traduzida para o texto de league.round da API-Football, e assim os nomes de
rodada e o formato fixo de cada copa (services/competicoes.py) são reaproveitados.
Placar = tempo normal + prorrogação (competitors[].score); pênaltis em competitors[].shootoutScore.
"""
import gzip
import json
import re
from datetime import date, datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.competicoes import fase_api_football, marcar_pode_penaltis
from services.importador_jogos import _parse_data_brasilia

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
# Liga ESPN -> id da liga na API-Football (formato fixo de rodadas em FORMATO_API_FOOTBALL).
FORMATO_DA_LIGA = {"conmebol.libertadores": "13", "conmebol.sudamericana": "11",
                   "bra.copa_do_brazil": "73", "bra.camp.mineiro": "629", "fifa.world": "1"}
# season.slug da ESPN -> league.round da API-Football. None = fase fora do bolão (ex.: Troféu Inconfidência).
FASES = {"first-stage": "1st Round", "second-stage": "2nd Round", "third-stage": "3rd Round",
         "first-round": "1st Round", "second-round": "2nd Round", "third-round": "3rd Round",
         "fourth-round": "4th Round", "fifth-round": "5th Round",
         "knockout-round-playoffs": "Knockout Round Play-offs", "round-of-32": "Round of 32",
         "round-of-16": "Round of 16",
         "quarterfinals": "Quarter-finals", "semifinals": "Semi-finals",
         "3rd-place-match": "Third Place", "third-place-match": "Third Place", "3rd-place-game": "Third Place",
         "final": "Final", "finals": "Final",
         "playoffs---semifinals": "Semi-finals",
         "playoffs---final": "Final", "playoffs---finals": "Final"}
FASES_IGNORADAS_PREFIXO = ("trofeu-inconfidencia",)


class ErroEspn(Exception):
    """Erro de consulta à ESPN (temporada ausente, resposta inválida…)."""


def _requisitar(liga, temporada):
    if not temporada:
        raise ErroEspn("Informe a temporada para sincronizar com a ESPN.")
    liga = str(liga or "").strip().casefold()
    if not re.fullmatch(r"[a-z0-9_]+(?:[.][a-z0-9_]+)+", liga):
        raise ErroEspn("Informe um código de liga ESPN válido.")
    if not re.fullmatch(r"[0-9]{4}", str(temporada)):
        raise ErroEspn("Informe a temporada ESPN com quatro dígitos.")
    url = f"{BASE_URL}/{liga}/scoreboard?" + urlencode({
        "dates": temporada, "limit": 1000, "lang": "pt", "region": "br"})
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"})
    try:
        with urlopen(req, timeout=60) as resposta:
            corpo = resposta.read()
        if corpo[:2] == b"\x1f\x8b":
            corpo = gzip.decompress(corpo)
        return json.loads(corpo)
    except (OSError, ValueError, EOFError) as exc:
        raise ErroEspn("Não foi possível consultar a ESPN: resposta inválida ou falha de conexão.") from exc


def _rodada_api_football(slug):
    if slug in FASES:
        return FASES[slug]
    if slug == "group-stage":
        return "Group Stage"
    if slug == "regular-season":
        return "Regular Season"
    return slug or "Fase não informada"


def _numero(valor):
    # Não truncar frações, aceitar booleanos ou transformar ausência em zero.
    if isinstance(valor, bool) or not re.fullmatch(r"[0-9]+", str(valor)):
        return None
    return int(valor)


def _data_evento(valor):
    if valor in (None, ""):
        return None
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("Data sem fuso")
    except (ValueError, TypeError, AttributeError) as exc:
        raise ErroEspn("ESPN: data de jogo inválida.") from exc
    return _parse_data_brasilia(valor)


STATUS_ESPECIAIS = {
    "STATUS_POSTPONED": "POSTPONED", "STATUS_CANCELED": "CANCELLED",
    "STATUS_CANCELLED": "CANCELLED", "STATUS_ABANDONED": "CANCELLED",
    "STATUS_SUSPENDED": "SUSPENDED", "STATUS_DELAYED": "SUSPENDED",
    "STATUS_HALFTIME": "PAUSED", "STATUS_AWARDED": "AWARDED",
}
STATUS_FINAIS = {"STATUS_FULL_TIME", "STATUS_FINAL", "STATUS_FINAL_AET", "STATUS_FINAL_PEN"}


def converter_eventos(dados):
    """Converte a resposta; rodadas de grupos/pontos corridos são inferidas (_inferir_rodadas).

    Uma lista vazia é válida; estrutura ausente/inválida é erro, evitando importar
    uma temporada parcialmente corrompida como se estivesse completa.
    """
    if (not isinstance(dados, dict) or dados.get("error") or dados.get("errors")
            or not isinstance(dados.get("events"), list)):
        raise ErroEspn("ESPN: resposta inválida; esperada uma lista de eventos.")
    jogos = []
    ids = set()
    for ev in dados["events"]:
        try:
            if not isinstance(ev, dict):
                raise ValueError("Evento inválido")
            slug = ((ev.get("season") or {}).get("slug") or "").strip().casefold()
            if slug.startswith(FASES_IGNORADAS_PREFIXO):
                continue
            eid = str(ev.get("id") or "").strip()
            if not eid or eid in ids:
                raise ValueError("ID ausente ou repetido")
            ids.add(eid)
            comp = ev["competitions"][0]
            competidores = comp["competitors"]
            lados = {c["homeAway"]: c for c in competidores}
            if len(competidores) != 2 or set(lados) != {"home", "away"}:
                raise ValueError("Participantes inválidos")
            casa, fora = lados["home"], lados["away"]
            nomes = [c["team"]["displayName"].strip() for c in (casa, fora)]
            if not all(nomes):
                raise ValueError("Time sem nome")
            tipo = (comp.get("status") or ev.get("status") or {}).get("type") or {}
            status_api = tipo.get("name")
            finalizado = (status_api in STATUS_FINAIS and tipo.get("completed") is True
                          and tipo.get("state") == "post")
            gols = [_numero(c.get("score")) for c in (casa, fora)] if finalizado else [None, None]
            if None in gols:
                gols = [None, None]
            pens = [_numero(c.get("shootoutScore")) for c in (casa, fora)] if finalizado else [None, None]
            if None in pens or None in gols:
                pens = [None, None]
            texto = _rodada_api_football(slug)
            if texto in ("Group Stage", "Regular Season"):
                estagio = "GROUP_STAGE" if texto == "Group Stage" else "REGULAR_SEASON"
                numero = None
                fase = "Fase de grupos" if texto == "Group Stage" else "Fase de liga"
            else:
                estagio, numero, fase = fase_api_football(texto)
            status = STATUS_ESPECIAIS.get(status_api) or (
                "FINISHED" if finalizado else "IN_PLAY" if tipo.get("state") == "in" else "SCHEDULED")
            if status_api == "STATUS_SCHEDULED":
                status = "TIMED" if comp.get("timeValid") is not False else "SCHEDULED"
            jogos.append({
                "external_id": eid, "estagio": estagio, "matchday": numero, "fase": fase,
                "time_casa": nomes[0], "time_fora": nomes[1],
                "data": _data_evento(comp.get("date") or ev.get("date")),
                "status": status, "status_api": status_api, "finalizado": finalizado,
                "gols_casa_real": gols[0], "gols_fora_real": gols[1],
                "penaltis_casa_real": pens[0], "penaltis_fora_real": pens[1],
            })
        except (KeyError, IndexError, TypeError, AttributeError, ValueError) as exc:
            raise ErroEspn("ESPN: evento inválido na resposta.") from exc
    _inferir_rodadas(jogos)
    marcar_pode_penaltis(jogos)
    return jogos


ESTAGIOS_INFERIDOS = ("GROUP_STAGE", "REGULAR_SEASON")


def _rodadas_do_estagio(jogos):
    """Rodada de cada jogo (mesma ordem de `jogos`) ou None se a tabela não fecha."""
    from services.sync import _normalizar_time

    ordem = sorted(range(len(jogos)), key=lambda i: (
        jogos[i]["data"] is None, jogos[i]["data"] or datetime.min, jogos[i]["external_id"]))
    times = [(_normalizar_time(j["time_casa"]), _normalizar_time(j["time_fora"])) for j in jogos]
    contagem, rodada = {}, [0] * len(jogos)
    for i in ordem:
        ordinais = []
        for time in times[i]:
            contagem[time] = contagem.get(time, 0) + 1
            ordinais.append(contagem[time])
        rodada[i] = max(ordinais)
    total = max(contagem.values())

    def ocupacao():
        ocupados = {}
        for i, par in enumerate(times):
            for time in par:
                ocupados.setdefault((time, rodada[i]), []).append(i)
        return ocupados

    # Adiamento: o jogo atrasado cai numa rodada em que os dois times já jogam; volta para a
    # primeira rodada em que nenhum dos dois jogou.
    for _ in range(len(jogos) * 2):
        ocupados = ocupacao()
        movido = False
        for i in ordem:
            if all(len(ocupados[(time, rodada[i])]) > 1 for time in times[i]):
                livres = [s for s in range(1, total + 1)
                          if all((time, s) not in ocupados for time in times[i])]
                if livres:
                    rodada[i], movido = livres[0], True
                    break
        if not movido:
            break
    if any(len(v) > 1 for v in ocupacao().values()) or max(rodada) > total:
        return None
    return rodada


def _inferir_rodadas(jogos):
    """Preenche 'matchday' em grupos/pontos corridos, que a ESPN não informa.

    Por estágio (com todos os jogos dele): rodada = maior ordinal cronológico do jogo entre os
    dois times, com reparo de adiamentos. Se a tabela não fechar (time repetido numa rodada ou
    mais rodadas que jogos de um time), o estágio inteiro fica sem matchday, sem inventar rodada.
    """
    for estagio in ESTAGIOS_INFERIDOS:
        do_estagio = [j for j in jogos if j["estagio"] == estagio and j["matchday"] is None]
        if not do_estagio:
            continue
        rodadas = _rodadas_do_estagio(do_estagio)
        if rodadas:
            for jogo, numero in zip(do_estagio, rodadas):
                jogo["matchday"] = numero
    return jogos


def _limite_data(valor):
    if valor in (None, ""):
        return None
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            return _data_evento(valor.isoformat()).date()
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError) as exc:
        raise ErroEspn("Filtro de data ESPN inválido; use AAAA-MM-DD.") from exc


def buscar_jogos_espn(liga, temporada=None, rodada=None, data_inicio=None, data_fim=None):
    """Filtra dias de Brasília inclusivos, após calcular os confrontos completos.

    Rodada numérica local é responsabilidade de sync.py, como na API-Football.
    """
    inicio, fim = _limite_data(data_inicio), _limite_data(data_fim)
    if inicio and fim and inicio > fim:
        raise ErroEspn("A data inicial deve ser anterior ou igual à data final.")
    jogos = converter_eventos(_requisitar(liga, temporada))
    return [j for j in jogos if (not inicio and not fim) or (
        j["data"] is not None and (not inicio or j["data"].date() >= inicio)
        and (not fim or j["data"].date() <= fim))]


def buscar_resultados_espn(liga, temporada=None, rodada=None, data_inicio=None, data_fim=None):
    return [{k: j[k] for k in ("external_id", "gols_casa_real", "gols_fora_real", "penaltis_casa_real",
                               "penaltis_fora_real", "data")}
            for j in buscar_jogos_espn(liga, temporada, rodada, data_inicio, data_fim)
            if j["finalizado"] and j["gols_casa_real"] is not None and j["gols_fora_real"] is not None]
