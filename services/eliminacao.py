"""Cortes cumulativos, calculados sem alterar participações ou palpites."""
from sqlalchemy.orm import selectinload

from models import Jogo, Rodada
from services.contexto_bolao import ordem_rodada
from services.elegibilidade import dentro_do_periodo


def participacoes_eliminadas(bolao, participacoes, *, ate_rodada=None):
    """Mapeia cada eliminado ao primeiro corte concluído em que caiu."""
    if not bolao or not bolao.eliminacao_participantes or not bolao.cortes_eliminacao:
        return {}
    from services.ranking import _calcular_ranking_sem_eliminacao

    cortes = sorted(bolao.cortes_eliminacao, key=lambda c: ordem_rodada(c.rodada))
    rodadas = Rodada.query.filter_by(campeonato_id=bolao.campeonato_id).options(
        selectinload(Rodada.jogos).joinedload(Jogo.resultado)).all()
    vivos = list(participacoes)
    eliminados, cache = {}, {}
    for corte in cortes:
        limite = ordem_rodada(corte.rodada)
        if ate_rodada and limite > ordem_rodada(ate_rodada):
            break
        if any(j.resultado is None for r in rodadas if ordem_rodada(r) <= limite for j in r.jogos):
            break
        # Quem desistiu até a rodada do corte não disputa nem ocupa vaga; entrada tardia disputa.
        vivos = [p for p in vivos
                 if not (p.status == 'desistente' and not dentro_do_periodo(p, corte.rodada))]
        ranking = _calcular_ranking_sem_eliminacao(
            bolao, ate_rodada=corte.rodada, todos=vivos, cache=cache)
        eliminados.update((i['participante'].id, corte) for i in ranking[corte.classificados:])
        vivos = [i['participante'] for i in ranking[:corte.classificados]]
    return eliminados


def eliminados_no_ranking(bolao, participacoes, rodada=None, *, ate_rodada=None):
    eliminados = participacoes_eliminadas(bolao, participacoes, ate_rodada=ate_rodada or rodada)
    return {pid: corte for pid, corte in eliminados.items()
            if rodada is None or ordem_rodada(corte.rodada) < ordem_rodada(rodada)}
