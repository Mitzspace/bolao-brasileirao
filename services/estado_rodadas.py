"""Estado de cada rodada calculado pelos jogos (não pelo campo manual "aberta").

- fechada:  todos os jogos têm resultado;
- pendente: a rodada já começou e ainda falta palpite de algum participante;
- aberta:   ainda há jogo sem resultado (e não falta palpite de rodada iniciada);
- sem_jogos: rodada cadastrada sem jogos.
"""
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database import db
from models import Jogo, Palpite, Participacao
from services.elegibilidade import participa_na_rodada
from services.relogio import agora_brasilia


def palpites_faltantes_por_rodada(bolao, rodadas):
    """{rodada_id: palpites que faltam} considerando quem participa de cada rodada."""
    ids = [r.id for r in rodadas]
    if not ids:
        return {}
    recebidos = {(p, r): n for p, r, n in db.session.query(
        Palpite.participacao_id, Jogo.rodada_id, func.count(Palpite.id))
        .join(Jogo, Jogo.id == Palpite.jogo_id)
        .join(Participacao, Participacao.id == Palpite.participacao_id)
        .filter(Participacao.bolao_id == bolao.id, Jogo.rodada_id.in_(ids),
                Palpite.excluido_por_desistencia.is_(False))
        .group_by(Palpite.participacao_id, Jogo.rodada_id).all()}
    pessoas = (Participacao.query.filter_by(bolao_id=bolao.id)
               .options(joinedload(Participacao.bolao), joinedload(Participacao.rodada_entrada),
                        joinedload(Participacao.rodada_desistencia)).all())
    faltantes = {}
    for r in rodadas:
        total = len(r.jogos)
        faltantes[r.id] = sum(max(0, total - recebidos.get((p.id, r.id), 0))
                              for p in pessoas if participa_na_rodada(p, r))
    return faltantes


def estado_rodada(rodada, faltantes, agora=None):
    jogos = rodada.jogos
    if not jogos:
        return 'sem_jogos'
    if all(j.resultado is not None for j in jogos):
        return 'fechada'
    agora = agora or agora_brasilia()
    iniciada = any(j.resultado is not None or j.encerrado or (j.data is not None and j.data <= agora) for j in jogos)
    return 'pendente' if iniciada and faltantes > 0 else 'aberta'


def estados_das_rodadas(bolao, rodadas):
    """{rodada_id: {'estado': ..., 'faltantes': n}}"""
    faltantes = palpites_faltantes_por_rodada(bolao, rodadas)
    agora = agora_brasilia()
    return {r.id: {'estado': estado_rodada(r, faltantes.get(r.id, 0), agora), 'faltantes': faltantes.get(r.id, 0)}
            for r in rodadas}
