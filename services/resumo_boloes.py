"""Resumo de gestão calculado em lote, sem alterar jogos ou palpites."""
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database import db
from models import Jogo, Palpite, Participacao, Resultado, Rodada
from services.contexto_bolao import ordem_rodada
from services.elegibilidade import participa_na_rodada


def rodadas_de_referencia(campeonato_ids):
    if not campeonato_ids:
        return {}
    rodadas = Rodada.query.filter(Rodada.campeonato_id.in_(campeonato_ids)).all()
    jogos = db.session.query(Jogo.rodada_id, Jogo.encerrado, Resultado.id).outerjoin(
        Resultado, Resultado.jogo_id == Jogo.id
    ).join(Rodada, Rodada.id == Jogo.rodada_id).filter(
        Rodada.campeonato_id.in_(campeonato_ids)).all()
    totais, em_andamento, iniciadas = {}, set(), set()
    for rodada_id, encerrado, resultado_id in jogos:
        totais[rodada_id] = totais.get(rodada_id, 0) + 1
        if not encerrado and resultado_id is None:
            em_andamento.add(rodada_id)
        else:
            iniciadas.add(rodada_id)
    referencias = {}
    for campeonato_id in campeonato_ids:
        opcoes = sorted((r for r in rodadas if r.campeonato_id == campeonato_id
                         and r.id in totais), key=ordem_rodada)
        # Rodada atual = a mais recente: jogos adiados de rodadas antigas não a "prendem".
        ultima_iniciada = next((r for r in reversed(opcoes) if r.id in iniciadas), None)
        pendentes = [r for r in opcoes if r.id in em_andamento and (
            ultima_iniciada is None or ordem_rodada(r) >= ordem_rodada(ultima_iniciada))]
        abertas = [r for r in pendentes if r.aberta]
        rodada = next(iter(abertas or pendentes), opcoes[-1] if opcoes else None)
        referencias[campeonato_id] = {
            'rodada': rodada,
            'ultima': bool(rodada and not pendentes),
            'jogos': totais.get(rodada.id, 0) if rodada else 0,
        }
    return referencias


def resumos_boloes(boloes):
    if not boloes:
        return {}
    ids = [b.id for b in boloes]
    referencias = rodadas_de_referencia({b.campeonato_id for b in boloes})
    ativos = dict(db.session.query(Participacao.bolao_id, func.count(Participacao.id))
        .filter(Participacao.bolao_id.in_(ids), Participacao.status == 'ativo')
        .group_by(Participacao.bolao_id).all())
    rodada_ids = [r['rodada'].id for r in referencias.values() if r['rodada']]
    recebidos = {(pessoa_id, rodada_id): total for pessoa_id, rodada_id, total in db.session.query(
        Participacao.id, Jogo.rodada_id, func.count(Palpite.id))
        .join(Palpite, Palpite.participacao_id == Participacao.id)
        .join(Jogo, Jogo.id == Palpite.jogo_id)
        .filter(Participacao.bolao_id.in_(ids), Palpite.excluido_por_desistencia.is_(False),
                Jogo.rodada_id.in_(rodada_ids))
        .group_by(Participacao.id, Jogo.rodada_id).all()} if rodada_ids else {}
    pessoas = (Participacao.query.filter(Participacao.bolao_id.in_(ids))
        .options(joinedload(Participacao.bolao), joinedload(Participacao.rodada_entrada),
                 joinedload(Participacao.rodada_desistencia)).all())
    resultado = {b.id: {
        **referencias[b.campeonato_id],
        'ativos': ativos.get(b.id, 0),
        'pendencias': 0,          # jogos em branco somados
        'pessoas_pendentes': 0,   # participantes com pelo menos um jogo em branco
    } for b in boloes}
    for pessoa in pessoas:
        ref = resultado[pessoa.bolao_id]
        if ref['rodada'] and participa_na_rodada(pessoa, ref['rodada']):
            faltam = max(0, ref['jogos'] - recebidos.get((pessoa.id, ref['rodada'].id), 0))
            ref['pendencias'] += faltam
            ref['pessoas_pendentes'] += 1 if faltam else 0
    return resultado


def participantes_pendentes(bolao, rodada):
    """Fonte para os próximos fluxos de lista e Salvar e próximo, por rodada."""
    if rodada.campeonato_id != bolao.campeonato_id:
        raise ValueError('Rodada de outro campeonato.')
    pessoas = Participacao.query.filter_by(bolao_id=bolao.id).order_by(Participacao.nome_exibicao, Participacao.id).all()
    recebidos = dict(db.session.query(Palpite.participacao_id, func.count(Palpite.id))
        .join(Jogo).join(Participacao).filter(Participacao.bolao_id == bolao.id,
             Jogo.rodada_id == rodada.id, Palpite.excluido_por_desistencia.is_(False))
        .group_by(Palpite.participacao_id).all())
    total = len(rodada.jogos)
    return [{'participacao': p, 'faltantes': total - recebidos.get(p.id, 0)} for p in pessoas
            if participa_na_rodada(p, rodada) and recebidos.get(p.id, 0) < total]
