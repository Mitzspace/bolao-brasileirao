"""Evolução rodada a rodada (pontos e posição) para o gráfico dos participantes.

Mesmo cálculo de services.ranking.calcular_ranking(ate_rodada=...), mas feito em
uma única passada: os pontos de cada palpite são calculados uma vez por rodada e
depois acumulados. A ordem de desempate é a mesma do ranking geral.
"""
from models import Jogo, Resultado, Rodada
from services.contexto_bolao import ordem_rodada
from services.elegibilidade import dentro_do_periodo, entra_no_ranking_da_rodada, palpite_elegivel
from services.pontuacao import calcular_pontuacao
from services.ranking import _chave_nome, carregar_participantes


def rodadas_com_resultado(campeonato_id):
    """Rodadas do campeonato que já têm ao menos um resultado, em ordem."""
    ids = {r.id for r in Rodada.query.join(Jogo, Jogo.rodada_id == Rodada.id)
           .join(Resultado, Resultado.jogo_id == Jogo.id)
           .filter(Rodada.campeonato_id == campeonato_id).distinct()}
    todas = sorted(Rodada.query.filter_by(campeonato_id=campeonato_id).all(), key=ordem_rodada)
    if not ids:
        return todas, []
    ultima = max(i for i, r in enumerate(todas) if r.id in ids)
    # Até a última rodada com resultado (inclui rodadas no meio sem resultado, como o ranking faz).
    return todas, todas[:ultima + 1]


def evolucao(bolao, todos=None):
    """{participacao_id: [{rodada, pontos, cravadas, palpites, acumulado, posicao, participa}]}"""
    if todos is None:
        todos = carregar_participantes(bolao)
    todas, rodadas = rodadas_com_resultado(bolao.campeonato_id)
    indice = {r.id: i for i, r in enumerate(todas)}
    n = len(todas)
    # Por rodada: pontos, cravadas, acertos de vencedor e quantidade de palpites lançados.
    por_rodada = {p.id: [[0, 0, 0, 0] for _ in range(n)] for p in todos}
    for p in todos:
        linhas = por_rodada[p.id]
        for pal in p.palpites:
            rodada = pal.jogo.rodada if pal.jogo else None
            if rodada is None or rodada.id not in indice:
                continue
            i = indice[rodada.id]
            linhas[i][3] += 1  # contagem inclui palpites guardados, como a tela atual
            if not palpite_elegivel(pal) or not pal.jogo.resultado:
                continue
            detalhe = calcular_pontuacao(pal, pal.jogo, pal.jogo.resultado)
            linhas[i][0] += detalhe.total
            if detalhe.placar_exato:
                linhas[i][1] += 1
            elif detalhe.acertou_resultado:
                linhas[i][2] += 1
        for b in p.creditos_historicos:
            if b.rodada is not None and b.rodada.id in indice and dentro_do_periodo(p, b.rodada):
                linhas[indice[b.rodada.id]][0] += b.pontos

    resultado = {p.id: [] for p in todos}
    acumulado = {p.id: [0, 0, 0] for p in todos}
    for rodada in rodadas:
        i = indice[rodada.id]
        for p in todos:
            pts, crav, acertos, _ = por_rodada[p.id][i]
            a = acumulado[p.id]
            a[0] += pts; a[1] += crav; a[2] += acertos
        ordem = sorted(todos, key=lambda p: (-acumulado[p.id][0], -acumulado[p.id][1],
                                             -acumulado[p.id][2], _chave_nome(p.nome)))
        posicoes = {p.id: pos for pos, p in enumerate(ordem, 1)}
        for p in todos:
            pts, crav, _, qtd = por_rodada[p.id][i]
            resultado[p.id].append({
                'rodada': rodada, 'pontos': pts, 'cravadas': crav, 'palpites': qtd,
                'acumulado': acumulado[p.id][0], 'posicao': posicoes[p.id],
                'participa': entra_no_ranking_da_rodada(p, rodada),
            })
    return resultado
