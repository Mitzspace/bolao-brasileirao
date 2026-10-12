"""Regra aprovada: a desistência informa a primeira rodada sem participação.

Rodada de entrada nula preserva a elegibilidade histórica, sem inventar datas.
"""
from services.contexto_bolao import ordem_rodada

REGRA_DESISTENCIA = "Primeira rodada em que não participa"


def dentro_do_periodo(participacao, rodada, *, saida=None, usar_saida_atual=True, incluir_antes_entrada=False):
    campeonato_id = participacao.bolao.campeonato_id or getattr(participacao.bolao.campeonato, 'id', None)
    campeonato_rodada = rodada.campeonato_id or getattr(rodada.campeonato, 'id', None)
    if campeonato_rodada != campeonato_id:
        return False
    entrada = participacao.rodada_entrada
    if (entrada and not incluir_antes_entrada
            and ordem_rodada(rodada) < ordem_rodada(entrada)):
        return False
    if usar_saida_atual:
        saida = participacao.rodada_desistencia
    if usar_saida_atual and participacao.status == "desistente" and saida is None:
        return False
    return saida is None or ordem_rodada(rodada) < ordem_rodada(saida)


def participa_na_rodada(participacao, rodada):
    """Lançamento e pendências: nunca cobrar rodadas anteriores à entrada."""
    return participacao.status not in {"removido", "saiu"} and dentro_do_periodo(participacao, rodada)


def entra_no_ranking_da_rodada(participacao, rodada):
    # Remoção administrativa não apaga os pontos históricos existentes.
    return dentro_do_periodo(participacao, rodada,
        incluir_antes_entrada=participacao.bolao.politica_entrada_tardia == "zero")


def palpite_elegivel(palpite):
    return (not palpite.excluido_por_desistencia
            and dentro_do_periodo(palpite.participacao, palpite.jogo.rodada))
