"""Grade de palpites da rodada (participantes × jogos), extraída de routes/participante.py.

Mantém a regra de privacidade: antes do início do jogo só o responsável (ou o
próprio dono) vê o palpite.
"""
from flask_login import current_user
from sqlalchemy.orm import joinedload

from models import BonusRodada, Jogo, Palpite, Participacao, Participante, ordem_dos_jogos
from services.contexto_bolao import responsavel_atual
from services.elegibilidade import dentro_do_periodo, entra_no_ranking_da_rodada, palpite_elegivel
from services.pontuacao import calcular_pontuacao
from services.ranking import _relacoes_palpite, _relacoes_participacao


def montar_grade(bolao, rodada):
    participantes = (Participacao.query.filter_by(bolao_id=bolao.id).options(*_relacoes_participacao()).order_by(Participacao.nome_exibicao).all()
                     if bolao else Participante.query.order_by(Participante.nome).all())
    if bolao:
        participantes = [p for p in participantes if entra_no_ranking_da_rodada(p, rodada)]
    jogos = (Jogo.query.filter_by(rodada_id=rodada.id).options(joinedload(Jogo.resultado))
             .order_by(*ordem_dos_jogos()).all())

    consulta = Palpite.query.options(*_relacoes_palpite()).join(Jogo).filter(Jogo.rodada_id == rodada.id)
    if bolao:
        consulta = consulta.join(Participacao).filter(Participacao.bolao_id == bolao.id)
    palpites_db = consulta.all()
    mapa_palpites = {((p.participacao_id if bolao else p.participante_id), p.jogo_id): p for p in palpites_db
                     if not bolao or palpite_elegivel(p)}

    matriz = []
    totais = {p.id: {"pontos": 0, "cravadas": 0} for p in participantes}
    for jogo in jogos:
        res = jogo.resultado
        linha = {"jogo": jogo, "resultado": res, "palpites": {}}
        for part in participantes:
            pal = mapa_palpites.get((part.id, jogo.id))
            dono = current_user.is_authenticated and (part.usuario_id == current_user.id if bolao else part.id == current_user.id)
            if not jogo.bloqueado() and not (responsavel_atual() or dono):
                pal = None
            pts = None
            eh_cravada = eh_vencedor = False
            if pal and res:
                detalhe = calcular_pontuacao(pal, jogo, res)
                pts = detalhe.total
                totais[part.id]["pontos"] += pts
                if detalhe.placar_exato:
                    eh_cravada = True
                    totais[part.id]["cravadas"] += 1
                elif detalhe.acertou_resultado:
                    eh_vencedor = True
            linha["palpites"][part.id] = {"palpite": pal, "pontos": pts, "cravada": eh_cravada, "vencedor": eh_vencedor}
        matriz.append(linha)

    bonus = BonusRodada.query.filter_by(rodada_id=rodada.id).options(
        joinedload(BonusRodada.participacao).options(*_relacoes_participacao())).all()
    bonus_db = {(b.participacao_id if bolao else b.participante_id): b.pontos for b in bonus
                if not bolao or (b.participacao.bolao_id == bolao.id and dentro_do_periodo(b.participacao, rodada))}
    for part in participantes:
        b_pts = bonus_db.get(part.id, 0)
        totais[part.id]["bonus"] = b_pts
        totais[part.id]["pontos"] += b_pts
    return participantes, jogos, matriz, totais, bonus_db
