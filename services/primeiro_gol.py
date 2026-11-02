"""Primeiro marcador dos jogos clássicos/especiais, preenchido pela ESPN (gratuita, sem chave).

Regras do bolão:
- só jogos clássicos/especiais (os únicos com palpite de primeiro gol);
- vale o autor do primeiro gol do jogo, inclusive gol contra;
- o que um responsável já digitou nunca é sobrescrito.

Para campeonatos da ESPN o autor já vem na mesma consulta dos placares (services/importador_espn).
Para os da football-data/API-Football, completar_primeiros_marcadores consulta o placar do dia na
ESPN só quando há clássico recente encerrado sem marcador, e casa o jogo pelos times e pela data.
"""
import logging
import time
from datetime import timedelta

from services.competicoes import FONTE_ESPN, normalizar_codigo_api, normalizar_fonte

logger = logging.getLogger(__name__)

# Código do campeonato na football-data / API-Football -> liga na ESPN.
LIGAS_ESPN = {
    "BSA": "bra.1", "71": "bra.1",
    "72": "bra.2",
    "CLI": "conmebol.libertadores", "13": "conmebol.libertadores",
    "11": "conmebol.sudamericana",
    "73": "bra.copa_do_brazil",
    "629": "bra.camp.mineiro",
    "WC": "fifa.world", "1": "fifa.world",
    "CL": "uefa.champions", "2": "uefa.champions",
    "PL": "eng.1", "39": "eng.1",
    "PD": "esp.1", "140": "esp.1",
    "SA": "ita.1", "135": "ita.1",
    "BL1": "ger.1", "78": "ger.1",
    "FL1": "fra.1", "61": "fra.1",
}
# Tolerância entre a data local do jogo e a da ESPN (adiamentos de horário, fuso).
TOLERANCIA_DATA = timedelta(days=2)
# Na sincronização periódica, só clássicos dos últimos dias; os antigos ficam com a conferência.
DIAS_RECENTES = 7
# Uma nova consulta do mesmo dia na ESPN no máximo a cada hora (jogo que não casa não insiste).
_INTERVALO_CONSULTA = 3600
_ultimas_consultas = {}


def marcador_vazio(jogo):
    return not (jogo.primeiro_marcador or "").strip()


def gravar_primeiro_marcador(jogo, resultado, marcador):
    """Grava o autor do primeiro gol se o jogo é especial, teve gol e ninguém digitou o marcador."""
    marcador = " ".join(str(marcador or "").split())[:100]
    if not marcador or not jogo.classico or not marcador_vazio(jogo):
        return False
    if resultado is None or (resultado.gols_casa_real or 0) + (resultado.gols_fora_real or 0) == 0:
        return False
    jogo.primeiro_marcador = marcador
    resultado.primeiro_gol_real = marcador
    return True


def liga_espn(campeonato):
    """Liga da ESPN equivalente ao campeonato (None se não houver correspondência conhecida)."""
    codigo = normalizar_codigo_api(campeonato.codigo_api)
    if not codigo:
        return None
    if normalizar_fonte(campeonato.fonte_api) == FONTE_ESPN:
        return codigo
    return LIGAS_ESPN.get(codigo.upper())


def eventos_espn(dados):
    """Eventos encerrados da resposta da ESPN, sem falhar por um evento malformado."""
    from services.importador_espn import STATUS_FINAIS, _data_evento, _numero, primeiro_gol_dos_detalhes
    eventos = []
    for ev in (dados or {}).get("events") or []:
        try:
            comp = ev["competitions"][0]
            lados = {c["homeAway"]: c for c in comp["competitors"]}
            casa, fora = lados["home"], lados["away"]
            tipo = (comp.get("status") or ev.get("status") or {}).get("type") or {}
            if not (tipo.get("name") in STATUS_FINAIS and tipo.get("completed") is True):
                continue
            eventos.append({
                "external_id": str(ev.get("id") or ""),
                "time_casa": casa["team"]["displayName"].strip(),
                "time_fora": fora["team"]["displayName"].strip(),
                "data": _data_evento(comp.get("date") or ev.get("date")),
                "gols_casa": _numero(casa.get("score")),
                "gols_fora": _numero(fora.get("score")),
                "tem_detalhes": "details" in comp,
                "primeiro_marcador": primeiro_gol_dos_detalhes(comp),
            })
        except Exception:  # um evento estranho não derruba os demais
            continue
    return eventos


def _juntar(eventos, novos):
    """Une listas de eventos; para o mesmo jogo, fica a versão que traz os lances."""
    por_id = {e["external_id"]: e for e in eventos}
    for e in novos:
        atual = por_id.get(e["external_id"])
        if atual is None or (e["tem_detalhes"] and not atual["tem_detalhes"]):
            por_id[e["external_id"]] = e
    return list(por_id.values())


def buscar_eventos(liga, temporada=None, dias=()):
    """Eventos encerrados da ESPN: a temporada inteira (uma consulta) e/ou dias avulsos."""
    from services.importador_espn import consultar_scoreboard
    eventos = []
    if temporada:
        eventos = eventos_espn(consultar_scoreboard(liga, str(temporada)))
    for dia in sorted(set(dias)):
        eventos = _juntar(eventos, eventos_espn(consultar_scoreboard(liga, dia.strftime("%Y%m%d"))))
    return eventos


def evento_do_jogo(jogo, eventos):
    """Evento da ESPN do mesmo confronto (mandante e visitante) e, se o jogo tem data, da mesma época.

    Sem data local só aceita um confronto único na lista; empate de candidatos devolve None.
    """
    from services.sync import _chave_jogo
    chave = _chave_jogo(jogo.time_casa, jogo.time_fora)
    candidatos = [e for e in eventos if _chave_jogo(e["time_casa"], e["time_fora"]) == chave]
    if jogo.data:
        candidatos = [e for e in candidatos if e["data"] and abs(e["data"] - jogo.data) <= TOLERANCIA_DATA]
    return candidatos[0] if len(candidatos) == 1 else None


def avaliar_jogo(jogo, eventos):
    """(situação, marcador da ESPN, evento) de um jogo especial encerrado sem marcador."""
    evento = evento_do_jogo(jogo, eventos)
    if evento is None:
        return "nao_encontrado", None, None
    resultado = jogo.resultado
    if (evento["gols_casa"], evento["gols_fora"]) != (resultado.gols_casa_real, resultado.gols_fora_real):
        return "placar_diferente", evento["primeiro_marcador"], evento
    if not evento["tem_detalhes"]:
        return "sem_lances", None, evento
    if not evento["primeiro_marcador"]:
        return "sem_nome", None, evento
    return "encontrado", evento["primeiro_marcador"], evento


def jogos_sem_marcador(campeonato_id, desde=None):
    """Clássicos encerrados, com gol, cujo primeiro marcador ainda está vazio."""
    from database import db
    from models import Jogo, Resultado, Rodada
    consulta = (Jogo.query.join(Rodada, Rodada.id == Jogo.rodada_id)
                .join(Resultado, Resultado.jogo_id == Jogo.id)
                .filter(Rodada.campeonato_id == campeonato_id, Jogo.classico.is_(True),
                        db.or_(Jogo.primeiro_marcador.is_(None), db.func.trim(Jogo.primeiro_marcador) == ""),
                        Resultado.gols_casa_real + Resultado.gols_fora_real > 0))
    if desde is not None:
        consulta = consulta.filter(Jogo.data.isnot(None), Jogo.data >= desde)
    return consulta.all()


def _dias_para_consultar(liga, jogos, agora):
    """Dia do jogo e o anterior (a ESPN data pelo horário dos EUA), sem repetir consulta recente."""
    dias = set()
    for jogo in jogos:
        for dia in (jogo.data.date(), jogo.data.date() - timedelta(days=1)):
            ultima = _ultimas_consultas.get((liga, dia))
            if ultima is None or agora - ultima >= _INTERVALO_CONSULTA:
                dias.add(dia)
    return dias


def completar_primeiros_marcadores(campeonatos, agora=None):
    """Passo da sincronização: preenche o marcador dos clássicos recentes que ficaram sem ele.

    Não consulta a ESPN quando não há jogo pendente. Devolve quantos jogos foram preenchidos.
    """
    from database import db
    from services.relogio import agora_brasilia
    agora = time.monotonic() if agora is None else agora
    desde = agora_brasilia() - timedelta(days=DIAS_RECENTES)
    preenchidos = 0
    for campeonato in campeonatos:
        liga = liga_espn(campeonato)
        if not liga:
            continue
        pendentes = jogos_sem_marcador(campeonato.id, desde=desde)
        dias = _dias_para_consultar(liga, pendentes, agora)
        if not dias:
            continue
        for dia in dias:
            _ultimas_consultas[(liga, dia)] = agora
        eventos = buscar_eventos(liga, dias=dias)
        for jogo in pendentes:
            situacao, marcador, _ = avaliar_jogo(jogo, eventos)
            if situacao == "encontrado" and gravar_primeiro_marcador(jogo, jogo.resultado, marcador):
                preenchidos += 1
        db.session.commit()
    return preenchidos
