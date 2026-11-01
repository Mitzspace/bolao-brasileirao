"""Possíveis ganhadores: chance estimada de cada participante e desempenho até aqui.

A estimativa é uma simulação de Monte Carlo dos jogos que faltam. Cada jogo simulado sorteia um
jogo já encerrado e todos repetem o que fizeram nele (cravou, acertou o resultado, errou). Assim:
- quem acerta mais tende a pontuar mais, e os palpites parecidos continuam parecidos: quando todos
  erram a mesma zebra, ninguém ganha terreno;
- os valores vêm das regras do bolão, conforme o jogo que falta seja clássico ou comum;
- jogo que pode ir para os pênaltis sorteia entre os jogos de mata-mata (com os pontos de pênaltis);
- cortes de eliminação que faltam são aplicados na ordem das rodadas, como em services/eliminacao.py.

Só entram os jogos já cadastrados: fases de copa ainda não importadas não são simuladas.
A semente depende do bolão e dos jogos encerrados, então a tela não muda ao recarregar.
Exclusivo da gestão: não há rota na área pública, que tem regras próprias de visibilidade.
"""
import random
from operator import add

from services.contexto_bolao import ordem_rodada
from services.elegibilidade import dentro_do_periodo, palpite_elegivel
from services.eliminacao import eliminados_no_ranking
from services.ranking import (_calcular_ranking_sem_eliminacao, _chave_nome, calcular_ranking,
                              carregar_participantes, pontuacao_palpite, pre_carregar_jogos)
from services.regras_pontuacao import regras_do_bolao

MAX_SIMULACOES = 5000
MIN_SIMULACOES = 1000
# Somas por simulação (jogos x participantes x simulações): limita o tempo na instância gratuita.
ORCAMENTO = 5_000_000
# Abaixo disto, a tela avisa que há pouco histórico para a estimativa.
JOGOS_PARA_CONFIAR = 20
RODADAS_RECENTES = 5

# Uma pontuação num inteiro só (pontos, cravadas, resultados): somar e comparar já segue o desempate.
_PESO_PONTOS = 10 ** 10
_PESO_CRAVADAS = 10 ** 5


def _codificar(pontos, cravadas, acertos):
    return pontos * _PESO_PONTOS + cravadas * _PESO_CRAVADAS + acertos


def _codificar_item(item):
    return _codificar(item['pontos'], item['cravadas'], item['acertos_vencedor'])


def _pontos(valor):
    return valor // _PESO_PONTOS


def _jogos_do_bolao(bolao):
    """(encerrados, restantes), na ordem das rodadas."""
    encerrados, restantes = [], []
    for jogo in pre_carregar_jogos(bolao.campeonato_id):
        (encerrados if jogo.resultado else restantes).append(jogo)
    chave = lambda j: (ordem_rodada(j.rodada), j.id)
    return sorted(encerrados, key=chave), sorted(restantes, key=chave)


def _pontos_exato(regras, jogo):
    return regras['classico_exato' if jogo.classico else 'comum_exato']


def _historico(pessoa, encerrados, regras, cache):
    """{jogo.id: pontuação} do que a pessoa fez nos jogos encerrados dentro do seu período."""
    ids = {j.id for j in encerrados}
    detalhes = {}
    for palpite in pessoa.palpites:
        if palpite.jogo_id in ids and palpite_elegivel(palpite):
            detalhes[palpite.jogo_id] = pontuacao_palpite(palpite, regras, cache)
    return detalhes


def _desempenho(pessoa, encerrados, detalhes, regras):
    """Números do participante nos jogos encerrados; jogo sem palpite conta como zero."""
    jogos = [j for j in encerrados if dentro_do_periodo(pessoa, j.rodada)]
    if not jogos:
        return {'jogos': 0, 'aproveitamento': None, 'mediaPorJogo': None, 'mediaRecente': None, 'melhorRodada': None}
    por_rodada = {}
    placar = maximo = 0
    for jogo in jogos:
        detalhe = detalhes.get(jogo.id)
        placar += detalhe.pontos_placar if detalhe else 0
        maximo += _pontos_exato(regras, jogo)
        pontos, total, _ = por_rodada.get(jogo.rodada.id, (0, 0, jogo.rodada))
        por_rodada[jogo.rodada.id] = (pontos + (detalhe.total if detalhe else 0), total + 1, jogo.rodada)
    rodadas = sorted(por_rodada.values(), key=lambda r: ordem_rodada(r[2]))
    recentes = rodadas[-RODADAS_RECENTES:]
    melhor = max(rodadas, key=lambda r: r[0])
    return {
        'jogos': len(jogos),
        # Só os pontos de placar: o bônus e os pênaltis não têm teto comparável entre os jogos.
        'aproveitamento': round(100 * placar / maximo, 1) if maximo else None,
        'mediaPorJogo': round(sum(r[0] for r in rodadas) / len(jogos), 2),
        'mediaRecente': round(sum(r[0] for r in recentes) / sum(r[1] for r in recentes), 2),
        'melhorRodada': {'nome': melhor[2].nome, 'pontos': melhor[0]},
    }


class _Simulacao:
    """Pré-calcula os vetores de pontos e sorteia os jogos que faltam."""

    def __init__(self, bolao, pessoas, base, encerrados, restantes, historicos, regras, cache):
        self.pessoas = pessoas
        self.base = base
        self.regras = regras
        self.encerrados = encerrados
        self.historicos = historicos
        self.disputam = [p.status == 'ativo' for p in pessoas]
        self.proprios = [[j for j in encerrados if j.id in h] for h in historicos]
        self.periodo = {}
        self.vetores = {}
        self.mata_mata = [j for j in encerrados if j.pode_penaltis]
        self.blocos = self._blocos(bolao, restantes, cache)

    def _participa(self, rodada):
        if rodada.id not in self.periodo:
            # Quem já não está ativo fica com os pontos que tem.
            self.periodo[rodada.id] = tuple(
                d and dentro_do_periodo(p, rodada) for p, d in zip(self.pessoas, self.disputam))
        return self.periodo[rodada.id]

    def _valor(self, indice, jogo_sorteado, classico, penaltis):
        """Valor do participante no jogo sorteado, com os pontos do jogo que está sendo simulado."""
        detalhes = self.historicos[indice]
        origem = jogo_sorteado
        if jogo_sorteado.id not in detalhes and not dentro_do_periodo(self.pessoas[indice], jogo_sorteado.rodada):
            # Entrou depois deste jogo: vale o que fez em outro; sem histórico, o de um colega.
            proprios = self.proprios[indice]
            if proprios:
                origem = proprios[jogo_sorteado.id % len(proprios)]
            else:
                com_palpite = [h for h in self.historicos if jogo_sorteado.id in h]
                detalhes = com_palpite[jogo_sorteado.id % len(com_palpite)] if com_palpite else {}
        detalhe = detalhes.get(origem.id)
        if detalhe is None:
            return 0
        modo = 'classico' if classico else 'comum'
        pontos = detalhe.pontos_bonus
        if detalhe.placar_exato:
            pontos += self.regras[f'{modo}_exato']
        elif detalhe.acertou_resultado:
            pontos += self.regras[f'{modo}_resultado']
        if penaltis:
            pontos += detalhe.pontos_penaltis
        return _codificar(pontos, int(detalhe.placar_exato),
                          int(detalhe.acertou_resultado and not detalhe.placar_exato))

    def _opcoes(self, jogo):
        """Um vetor (um valor por participante) para cada jogo que pode ser sorteado."""
        penaltis = bool(jogo.pode_penaltis)
        participa = self._participa(jogo.rodada)
        chave = (bool(jogo.classico), penaltis, participa)
        if chave not in self.vetores:
            fonte = self.mata_mata if penaltis and self.mata_mata else self.encerrados
            self.vetores[chave] = [
                [self._valor(i, sorteado, chave[0], penaltis) if participa[i] else 0 for i in range(len(self.pessoas))]
                for sorteado in fonte]
        return self.vetores[chave]

    def _blocos(self, bolao, restantes, cache):
        """[(opções de cada jogo, corte ao final do bloco)], na ordem das rodadas."""
        blocos, fila = [], list(restantes)
        if bolao.eliminacao_participantes:
            for corte in sorted(bolao.cortes_eliminacao, key=lambda c: ordem_rodada(c.rodada)):
                ordem = ordem_rodada(corte.rodada)
                agora = [j for j in fila if ordem_rodada(j.rodada) <= ordem]
                if not agora and not blocos:
                    continue  # corte já concluído: quem caiu nem está na lista
                fila = fila[len(agora):]
                # Pontos reais até a rodada do corte; o que veio depois dele não conta nesse corte.
                parcial = _calcular_ranking_sem_eliminacao(bolao, ate_rodada=corte.rodada, todos=self.pessoas, cache=cache)
                pontos = {i['participante'].id: _codificar_item(i) for i in parcial}
                blocos.append(([self._opcoes(j) for j in agora], {
                    'classificados': corte.classificados,
                    'base': [pontos[p.id] for p in self.pessoas],
                    'fora': {i for i, p in enumerate(self.pessoas)
                             if p.status == 'desistente' and not dentro_do_periodo(p, corte.rodada)},
                }))
        blocos.append(([self._opcoes(j) for j in fila], None))
        return blocos

    def rodar(self, simulacoes, semente):
        rng = random.Random(semente)
        n = len(self.pessoas)
        vitorias, podios, somas = [0] * n, [0] * n, [0] * n
        for _ in range(simulacoes):
            acumulado = [0] * n
            vivos = range(n)  # em ordem de nome: empate total fica com o primeiro, como no ranking
            for opcoes, corte in self.blocos:
                for vetores in opcoes:
                    acumulado = list(map(add, acumulado, rng.choice(vetores)))
                if corte:
                    parcial = list(map(add, corte['base'], acumulado))
                    ordem = sorted((i for i in vivos if i not in corte['fora']), key=lambda i: -parcial[i])
                    vivos = sorted(ordem[:corte['classificados']])
            final = list(map(add, self.base, acumulado))
            somas = list(map(add, somas, final))
            ordem = sorted((i for i in vivos if self.disputam[i]), key=lambda i: -final[i])
            if ordem:
                vitorias[ordem[0]] += 1
            for i in ordem[:3]:
                podios[i] += 1
        return vitorias, podios, somas


def _pontos_maximos(pessoa, pontos, restantes, regras):
    if pessoa.status != 'ativo':
        return pontos
    return pontos + sum(
        _pontos_exato(regras, j) + regras['primeiro_gol'] + (regras['penaltis_exato'] if j.pode_penaltis else 0)
        for j in restantes if dentro_do_periodo(pessoa, j.rodada))


def _situacao(bolao, ativos, encerrados, restantes):
    if bolao.status == 'desistido':
        return 'desistido'
    if bolao.status == 'finalizado':
        return 'encerrado'
    if not ativos:
        return 'sem_participantes'
    if not encerrados or not ativos[0]['pontos']:
        return 'sem_resultados'  # sem pontos, não há diferença entre os participantes para estimar
    return 'simulada' if restantes else 'sem_jogos'


def possiveis_ganhadores(bolao):
    """Chance de título e desempenho de quem ainda disputa."""
    regras = regras_do_bolao(bolao)
    todos = carregar_participantes(bolao)
    cache = {}
    ranking = calcular_ranking(bolao, todos=todos, cache=cache)
    encerrados, restantes = _jogos_do_bolao(bolao)
    copa = bool(bolao.eliminacao_participantes or any(j.pode_penaltis for j in encerrados + restantes))
    ativos = [i for i in ranking if i['participante'].status == 'ativo']
    situacao = _situacao(bolao, ativos, encerrados, restantes)

    pessoas = sorted((i['participante'] for i in ranking), key=lambda p: _chave_nome(p.nome))
    historicos = [_historico(p, encerrados, regras, cache) for p in pessoas]
    desempenho = {p.id: _desempenho(p, encerrados, h, regras) for p, h in zip(pessoas, historicos)}

    simulacoes = 0
    chances = {}
    if situacao == 'simulada':
        simulacoes = max(MIN_SIMULACOES, min(MAX_SIMULACOES, ORCAMENTO // (len(restantes) * len(pessoas))))
        itens = {i['participante'].id: i for i in ranking}
        base = [_codificar_item(itens[p.id]) for p in pessoas]
        simulacao = _Simulacao(bolao, pessoas, base, encerrados, restantes, historicos, regras, cache)
        vitorias, podios, somas = simulacao.rodar(simulacoes, bolao.id * 1_000_003 + len(encerrados))
        chances = {p.id: (100 * v / simulacoes, 100 * t / simulacoes, _pontos(s) / simulacoes)
                   for p, v, t, s in zip(pessoas, vitorias, podios, somas)}
    elif ativos and ativos[0]['pontos'] and situacao in ('sem_jogos', 'encerrado'):
        # Decidido: o líder leva.
        chances = {i['participante'].id: (100.0 if n == 0 else 0.0, 100.0 if n < 3 else 0.0, i['pontos'])
                   for n, i in enumerate(ativos)}

    lider = ativos[0]['pontos'] if ativos else 0
    linhas = []
    for posicao, item in enumerate(ativos, 1):
        pessoa = item['participante']
        chance = chances.get(pessoa.id)
        maximo = _pontos_maximos(pessoa, item['pontos'], restantes, regras)
        linhas.append({
            'participacaoId': pessoa.id,
            'nome': pessoa.nome,
            'posicao': posicao,
            'pontos': item['pontos'],
            'cravadas': item['cravadas'],
            'acertos': item['acertos_vencedor'],
            'distanciaLider': lider - item['pontos'],
            'pontosMaximos': maximo,
            # Mesmo que nenhuma simulação o coloque em 1º, só está fora quem não alcança mais o líder.
            'semChance': maximo < lider,
            'probabilidade': round(chance[0], 1) if chance else None,
            'chancePodio': round(chance[1], 1) if chance else None,
            'pontosProjetados': round(chance[2], 1) if chance else None,
            'desempenho': desempenho[pessoa.id],
        })
    linhas.sort(key=lambda l: (-(l['probabilidade'] or 0), l['posicao']))

    return {
        'situacao': situacao,
        'copa': copa,
        'simulacoes': simulacoes,
        'jogosEncerrados': len(encerrados),
        'jogosRestantes': len(restantes),
        'rodadasRestantes': len({j.rodada_id for j in restantes}),
        'poucosDados': situacao == 'simulada' and len(encerrados) < JOGOS_PARA_CONFIAR,
        'eliminados': len(eliminados_no_ranking(bolao, todos)),
        'desistentes': sum(1 for i in ranking if i['participante'].status == 'desistente'),
        'participantes': linhas,
    }
