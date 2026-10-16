"""Classificação do bolão, compartilhada pela tela atual (/ranking) e pela nova interface.

O cálculo é exatamente o que existia em routes/participante.ranking; apenas foi
movido para cá. A opção `ate_rodada` (acumulado até uma rodada) é usada só para
a variação de posição e não altera o ranking geral nem o por rodada.
"""
import unicodedata

from flask import g, has_app_context
from sqlalchemy.orm import joinedload, selectinload

from database import db
from models import Bolao, BonusRodada, Jogo, Palpite, Participante, Participacao, Resultado, Rodada
from services.contexto_bolao import ordem_rodada
from services.elegibilidade import dentro_do_periodo, entra_no_ranking_da_rodada, palpite_elegivel
from services.pontuacao import calcular_pontuacao
from services.regras_pontuacao import regras_do_bolao


def _relacoes_participacao():
    return (joinedload(Participacao.bolao), joinedload(Participacao.rodada_entrada),
            joinedload(Participacao.rodada_desistencia))


def _relacoes_palpite():
    return (joinedload(Palpite.jogo).joinedload(Jogo.resultado),
            joinedload(Palpite.jogo).joinedload(Jogo.rodada).joinedload(Rodada.campeonato),
            joinedload(Palpite.participacao).options(*_relacoes_participacao()))


def pre_carregar_jogos(campeonato_id):
    """Jogos do campeonato com rodada e resultado em uma consulta.

    Depois disso, palpite.jogo, jogo.rodada e as rodadas de entrada/desistência
    saem da memória da sessão sem nova consulta, e cada jogo aparece uma vez
    (antes vinha repetido em cada uma das ~6.000 linhas de palpite).
    """
    jogos = (Jogo.query.join(Rodada, Rodada.id == Jogo.rodada_id)
             .filter(Rodada.campeonato_id == campeonato_id)
             .options(joinedload(Jogo.resultado), joinedload(Jogo.rodada)).all())
    if has_app_context():
        # A sessão guarda objetos por referência fraca: mantém-os vivos até o fim da requisição.
        g.setdefault('_jogos_pre_carregados', []).append(jogos)
    return jogos


def carregar_participantes(bolao):
    """Participações do bolão (ou participantes do modo legado sem bolões)."""
    if bolao:
        pre_carregar_jogos(bolao.campeonato_id)
        return Participacao.query.filter_by(bolao_id=bolao.id).options(
            *_relacoes_participacao(),
            selectinload(Participacao.palpites),
            selectinload(Participacao.creditos_historicos)).all()
    if Bolao.query.first():
        return []
    return Participante.query.options(
        selectinload(Participante.palpites).options(*_relacoes_palpite()),
        selectinload(Participante.bonus_list).joinedload(BonusRodada.rodada)).all()


def _chave_nome(nome):
    return "".join(c for c in unicodedata.normalize("NFKD", nome.casefold())
                   if not unicodedata.combining(c))


def pontuacao_palpite(pal, regras, cache):
    """calcular_pontuacao com as regras do bolão já resolvidas e memória por palpite."""
    if cache is None:
        return calcular_pontuacao(pal, pal.jogo, pal.jogo.resultado, regras)
    detalhe = cache.get(pal.id)
    if detalhe is None:
        detalhe = cache[pal.id] = calcular_pontuacao(pal, pal.jogo, pal.jogo.resultado, regras)
    return detalhe


def calcular_ranking(bolao, rodada=None, ocultar_desistentes=False, *, ate_rodada=None, todos=None, cache=None):
    """Lista ordenada de dicionários (participante, pontos, bônus, cravadas...).

    rodada: ranking somente daquela rodada (comportamento da tela atual).
    ate_rodada: ranking acumulado até a rodada informada, inclusive.
    todos: participações já carregadas (evita consultar de novo).
    cache: dicionário compartilhado entre chamadas com os mesmos `todos` (pontuação por palpite).
    """
    regras = regras_do_bolao(bolao) if bolao else None
    if todos is None:
        todos = carregar_participantes(bolao)
    limite = ordem_rodada(ate_rodada) if ate_rodada else None

    def _considerar(rodada_item):
        if rodada and (rodada_item is None or rodada_item.id != rodada.id):
            return False
        return limite is None or (rodada_item is not None and ordem_rodada(rodada_item) <= limite)

    # A resposta só depende da rodada: calculada uma vez por rodada, não por palpite.
    consideradas = {}

    def considerar(rodada_item):
        chave = rodada_item.id if rodada_item is not None else None
        if chave not in consideradas:
            consideradas[chave] = _considerar(rodada_item)
        return consideradas[chave]

    resultado = []
    for p in todos:
        if bolao and (ocultar_desistentes and p.status == 'desistente'
                      or rodada and not entra_no_ranking_da_rodada(p, rodada)):
            continue
        total_palpites = cravadas = acertos_vencedor = bonus_primeiro_gol = 0
        no_periodo = {}  # palpite_elegivel(pal) por rodada desta participação
        for pal in p.palpites:
            if bolao:
                if pal.excluido_por_desistencia:
                    continue
                rodada_pal = pal.jogo.rodada
                if rodada_pal.id not in no_periodo:
                    no_periodo[rodada_pal.id] = palpite_elegivel(pal)
                if not no_periodo[rodada_pal.id]:
                    continue
            if not considerar(pal.jogo.rodada):
                continue
            if pal.jogo and pal.jogo.resultado:
                detalhe = pontuacao_palpite(pal, regras, cache)
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
    cache = {}
    atual = calcular_ranking(bolao, ocultar_desistentes=ocultar_desistentes, todos=todos, cache=cache)
    ultima = ultima_rodada_com_resultado(bolao.campeonato_id) if bolao else None
    anteriores = []
    if ultima:
        rodadas = sorted(Rodada.query.filter_by(campeonato_id=bolao.campeonato_id).all(), key=ordem_rodada)
        anteriores = [r for r in rodadas if ordem_rodada(r) < ordem_rodada(ultima)]
    posicoes_antes = {}
    if anteriores:
        antes = calcular_ranking(bolao, ocultar_desistentes=ocultar_desistentes,
                                 ate_rodada=anteriores[-1], todos=todos, cache=cache)
        posicoes_antes = {item["participante"].id: i for i, item in enumerate(antes, 1)}
    for posicao, item in enumerate(atual, 1):
        anterior = posicoes_antes.get(item["participante"].id)
        item["posicao"] = posicao
        item["variacao"] = (anterior - posicao) if anterior is not None else None
    return atual, ultima
