"""Classificação do bolão, compartilhada pela tela atual (/ranking) e pela nova interface.

O cálculo é exatamente o que existia em routes/participante.ranking; apenas foi
movido para cá. A opção `ate_rodada` (acumulado até uma rodada) é usada só para
a variação de posição e não altera o ranking geral nem o por rodada.
"""
import unicodedata

from sqlalchemy.orm import joinedload, selectinload

from database import db
from models import Bolao, BonusRodada, Jogo, Palpite, Participante, Participacao, Resultado, Rodada
from services.contexto_bolao import ordem_rodada
from services.elegibilidade import dentro_do_periodo, entra_no_ranking_da_rodada, palpite_elegivel
from services.pontuacao import calcular_pontuacao


def _relacoes_participacao():
    return (joinedload(Participacao.bolao), joinedload(Participacao.rodada_entrada),
            joinedload(Participacao.rodada_desistencia))


def _relacoes_palpite():
    return (joinedload(Palpite.jogo).joinedload(Jogo.resultado),
            joinedload(Palpite.jogo).joinedload(Jogo.rodada).joinedload(Rodada.campeonato),
            joinedload(Palpite.participacao).options(*_relacoes_participacao()))


def carregar_participantes(bolao):
    """Participações do bolão (ou participantes do modo legado sem bolões)."""
    if bolao:
        return Participacao.query.filter_by(bolao_id=bolao.id).options(
            *_relacoes_participacao(),
            selectinload(Participacao.palpites).options(*_relacoes_palpite()),
            selectinload(Participacao.creditos_historicos).joinedload(BonusRodada.rodada)).all()
    if Bolao.query.first():
        return []
    return Participante.query.options(
        selectinload(Participante.palpites).options(*_relacoes_palpite()),
        selectinload(Participante.bonus_list).joinedload(BonusRodada.rodada)).all()


def _chave_nome(nome):
    return "".join(c for c in unicodedata.normalize("NFKD", nome.casefold())
                   if not unicodedata.combining(c))


def calcular_ranking(bolao, rodada=None, ocultar_desistentes=False, *, ate_rodada=None, todos=None):
    """Lista ordenada de dicionários (participante, pontos, bônus, cravadas...).

    rodada: ranking somente daquela rodada (comportamento da tela atual).
    ate_rodada: ranking acumulado até a rodada informada, inclusive.
    todos: participações já carregadas (evita consultar de novo).
    """
    if todos is None:
        todos = carregar_participantes(bolao)
    limite = ordem_rodada(ate_rodada) if ate_rodada else None

    def considerar(rodada_item):
        if rodada and (rodada_item is None or rodada_item.id != rodada.id):
            return False
        return limite is None or (rodada_item is not None and ordem_rodada(rodada_item) <= limite)

    resultado = []
    for p in todos:
        if bolao and (ocultar_desistentes and p.status == 'desistente'
                      or rodada and not entra_no_ranking_da_rodada(p, rodada)):
            continue
        total_palpites = cravadas = acertos_vencedor = bonus_primeiro_gol = 0
        for pal in p.palpites:
            if bolao and not palpite_elegivel(pal):
                continue
            if not considerar(pal.jogo.rodada):
                continue
            if pal.jogo and pal.jogo.resultado:
                detalhe = calcular_pontuacao(pal, pal.jogo, pal.jogo.resultado)
                total_palpites += detalhe.total
                bonus_primeiro_gol += detalhe.pontos_bonus
                if detalhe.placar_exato:
                    cravadas += 1
                elif detalhe.acertou_resultado:
                    acertos_vencedor += 1

        total_bonus = sum(b.pontos for b in (p.creditos_historicos if bolao else p.bonus_list)
                          if considerar(b.rodada)
                          and (not bolao or dentro_do_periodo(p, b.rodada)))
        resultado.append({
            "participante": p,
            "pontos": total_palpites + total_bonus,
            "pontos_palpites": total_palpites,
            "bonus": total_bonus,
            "bonus_primeiro_gol": bonus_primeiro_gol,
            "cravadas": cravadas,
            "acertos_vencedor": acertos_vencedor,
        })

    # Pontos, placares exatos, acertos de vencedor/empate e nome.
    resultado.sort(key=lambda i: (-i["pontos"], -i["cravadas"], -i["acertos_vencedor"],
                                  _chave_nome(i["participante"].nome)))
    return resultado


def ultima_rodada_com_resultado(campeonato_id):
    rodadas = (Rodada.query.join(Jogo, Jogo.rodada_id == Rodada.id)
               .join(Resultado, Resultado.jogo_id == Jogo.id)
               .filter(Rodada.campeonato_id == campeonato_id).distinct().all())
    return max(rodadas, key=ordem_rodada) if rodadas else None


def ranking_com_variacao(bolao, ocultar_desistentes=False):
    """Ranking geral + variação de posição em relação à rodada anterior à última com resultado.

    variacao > 0: subiu; < 0: caiu; 0: manteve; None: sem comparação possível.
    """
    todos = carregar_participantes(bolao)
    atual = calcular_ranking(bolao, ocultar_desistentes=ocultar_desistentes, todos=todos)
    ultima = ultima_rodada_com_resultado(bolao.campeonato_id) if bolao else None
    anteriores = []
    if ultima:
        rodadas = sorted(Rodada.query.filter_by(campeonato_id=bolao.campeonato_id).all(), key=ordem_rodada)
        anteriores = [r for r in rodadas if ordem_rodada(r) < ordem_rodada(ultima)]
    posicoes_antes = {}
    if anteriores:
        antes = calcular_ranking(bolao, ocultar_desistentes=ocultar_desistentes,
                                 ate_rodada=anteriores[-1], todos=todos)
        posicoes_antes = {item["participante"].id: i for i, item in enumerate(antes, 1)}
    for posicao, item in enumerate(atual, 1):
        anterior = posicoes_antes.get(item["participante"].id)
        item["posicao"] = posicao
        item["variacao"] = (anterior - posicao) if anterior is not None else None
    return atual, ultima
