"""Dados da área pública (somente leitura, acesso por link, sem login).

Regras de visibilidade, aplicadas AQUI no servidor (o JSON nunca contém o que é restrito):
- Palpites só das rodadas LIBERADAS pelo admin (bolao.rodada_publica) e, dentro delas, só de
  jogos com RESULTADO registrado. A consulta ao banco já filtra por esses jogos: palpites de
  rodadas não liberadas ou de jogos futuros nem são lidos. Sem rodada liberada, nenhum palpite sai.
- Pontos, classificação e desempenho por participante só até a rodada liberada.
- Nada de palpites faltantes, e-mails, observações, motivo de desistência, ids internos ou dados
  de conta. Rodadas são identificadas pelo número de ordem (1, 2, 3...), não pelo id do banco, e
  participantes por uma referência opaca (HMAC do código do link), que muda quando o link é regerado.
"""
import hashlib
import hmac
import re
from datetime import datetime

from flask import current_app
from sqlalchemy.orm import joinedload

from models import Bolao, Jogo, Palpite, Participacao, ordem_dos_jogos
from routes.api_serializacao import serializar_regras, texto_data
from services.contexto_bolao import opcoes_rodadas, ordem_rodada
from services.elegibilidade import entra_no_ranking_da_rodada, palpite_elegivel
from services.eliminacao import eliminados_no_ranking
from services.escudos import escudo_time
from services.evolucao_ranking import evolucao, rotulo_curto
from services.pontuacao import calcular_pontuacao
from services.ranking import calcular_ranking, carregar_participantes
from services.regras_pontuacao import regras_do_bolao
from services.relogio import agora_brasilia
from services.resumo_boloes import rodadas_de_referencia
from services.tabela_campeonato import dados_tabela

FORMATO_CODIGO = re.compile(r'[A-Za-z0-9_-]{16,64}')
FORMATO_REF = re.compile(r'[0-9a-f]{16}')
STATUS_VISIVEIS = ('ativo', 'desistente')


def bolao_do_codigo(codigo):
    """Bolão do link público, ou None (código mal formado, inexistente ou revogado)."""
    if not codigo or not FORMATO_CODIGO.fullmatch(codigo):
        return None
    return (Bolao.query.options(joinedload(Bolao.campeonato), joinedload(Bolao.rodada_publica))
            .filter(Bolao.codigo_publico == codigo).first())


def referencia(bolao, pessoa):
    """Referência pública e estável de um participante, sem expor o id do banco.

    HMAC(SECRET_KEY, código do link + id): não dá para adivinhar nem enumerar, e
    deixa de valer quando o admin gera um novo link.
    """
    chave = str(current_app.secret_key or '').encode()
    mensagem = f'{bolao.codigo_publico}:{pessoa.id}'.encode()
    return hmac.new(chave, mensagem, hashlib.sha256).hexdigest()[:16]


# ---------- rodadas ----------

class Contexto:
    """Rodadas do campeonato em ordem, com número público (1, 2, 3...) e rodada liberada."""

    def __init__(self, bolao):
        self.bolao = bolao
        self.rodadas = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
        self.numero = {r.id: i for i, r in enumerate(self.rodadas, 1)}
        liberada = bolao.rodada_publica
        self.liberada_ate = self.numero.get(liberada.id) if liberada else None

    def rodada(self, numero):
        if isinstance(numero, int) and 1 <= numero <= len(self.rodadas):
            return self.rodadas[numero - 1]
        return None

    def pontos_liberados(self, rodada):
        return self.liberada_ate is not None and self.numero[rodada.id] <= self.liberada_ate

    # Palpites seguem a mesma liberação dos pontos: rodada posterior à liberada fica oculta.
    palpites_liberados = pontos_liberados

    def referencia(self):
        rodada = rodadas_de_referencia({self.bolao.campeonato_id})[self.bolao.campeonato_id]['rodada']
        return rodada if rodada is not None and rodada.id in self.numero else (self.rodadas[0] if self.rodadas else None)

    def ultima_com_resultado(self, ate=None):
        rodadas = self.rodadas[:ate] if ate is not None else self.rodadas
        return next((r for r in reversed(rodadas) if any(tem_resultado(j) for j in r.jogos)), None)

    def resumo_rodada(self, rodada):
        jogos = rodada.jogos
        agora = agora_brasilia()
        if jogos and all(tem_resultado(j) for j in jogos):
            situacao = 'encerrada'
        elif any(tem_resultado(j) or (j.data is not None and j.data <= agora) for j in jogos):
            situacao = 'andamento'
        else:
            situacao = 'agendada'
        return {'numero': self.numero[rodada.id], 'nome': rodada.nome, 'situacao': situacao,
                'comResultado': sum(1 for j in jogos if tem_resultado(j)), 'jogos': len(jogos),
                'palpitesLiberados': self.palpites_liberados(rodada)}

    def lista_rodadas(self):
        return [self.resumo_rodada(r) for r in self.rodadas]

    def liberada(self):
        if self.liberada_ate is None:
            return None
        return {'numero': self.liberada_ate, 'nome': self.rodadas[self.liberada_ate - 1].nome}

    def referencia_variacao(self):
        """Nome da rodada usada como "antes" na variação de posição (a anterior à liberada)."""
        if self.liberada_ate is None or self.liberada_ate < 2:
            return None
        return self.rodadas[self.liberada_ate - 2].nome


def tem_resultado(jogo):
    r = jogo.resultado
    return r is not None and r.gols_casa_real is not None and r.gols_fora_real is not None


def _status(jogo, agora):
    if tem_resultado(jogo):
        return 'encerrado'
    if jogo.data is not None and jogo.data <= agora:
        return 'aguardando'
    return 'agendado'


def jogo_publico(jogo, campeonato_id, agora, numero=None):
    resultado = jogo.resultado if tem_resultado(jogo) else None
    dados = {
        'casa': jogo.time_casa, 'fora': jogo.time_fora,
        'escudoCasa': escudo_time(jogo.time_casa, campeonato_id=campeonato_id),
        'escudoFora': escudo_time(jogo.time_fora, campeonato_id=campeonato_id),
        'data': jogo.data.isoformat() if jogo.data else None,
        'dataTexto': texto_data(jogo.data),
        'classico': bool(jogo.classico),
        'status': _status(jogo, agora),
        'golsCasa': resultado.gols_casa_real if resultado else None,
        'golsFora': resultado.gols_fora_real if resultado else None,
        'penaltisCasa': resultado.penaltis_casa_real if resultado else None,
        'penaltisFora': resultado.penaltis_fora_real if resultado else None,
    }
    if numero is not None:
        dados['numero'] = numero
    return dados


def _por_horario(jogos):
    return sorted(jogos, key=lambda j: (j.data is None, j.data or datetime.min, j.id))


# ---------- classificação ----------

def _itens_ranking(bolao, ranking):
    return [{
        'posicao': i, 'ref': referencia(bolao, item['participante']), 'nome': item['participante'].nome,
        'status': getattr(item['participante'], 'status', 'ativo'),
        'pontos': item['pontos'], 'pontosPalpites': item['pontos_palpites'], 'bonus': item['bonus'],
        'bonusPrimeiroGol': item['bonus_primeiro_gol'],
        'cravadas': item['cravadas'], 'acertos': item['acertos_vencedor'], 'variacao': item.get('variacao'),
    } for i, item in enumerate(ranking, 1)]


def ranking_liberado(ctx, ocultar_desistentes=True, numero=None, todos=None):
    """Classificação geral até a rodada liberada, ou de uma rodada (≤ liberada). None se oculta."""
    if ctx.liberada_ate is None:
        return None
    if numero is not None and not (isinstance(numero, int) and 1 <= numero <= ctx.liberada_ate):
        return None
    todos = todos if todos is not None else carregar_participantes(ctx.bolao)
    if numero is not None:
        return calcular_ranking(ctx.bolao, ctx.rodada(numero), ocultar_desistentes, todos=todos)
    limite = ctx.rodada(ctx.liberada_ate)
    cache = {}
    atual = calcular_ranking(ctx.bolao, ocultar_desistentes=ocultar_desistentes, ate_rodada=limite,
                             todos=todos, cache=cache)
    if ctx.liberada_ate > 1:
        antes = calcular_ranking(ctx.bolao, ocultar_desistentes=ocultar_desistentes,
                                 ate_rodada=ctx.rodada(ctx.liberada_ate - 1), todos=todos, cache=cache)
        posicoes = {item['participante'].id: i for i, item in enumerate(antes, 1)}
        for posicao, item in enumerate(atual, 1):
            anterior = posicoes.get(item['participante'].id)
            item['variacao'] = (anterior - posicao) if anterior is not None else None
    return atual


def classificacao(bolao, numero=None, ocultar_desistentes=True):
    ctx = Contexto(bolao)
    if ctx.liberada_ate is None:
        return {'liberada': False}
    ranking = ranking_liberado(ctx, ocultar_desistentes, numero)
    if ranking is None:
        return None  # rodada inexistente ou ainda não liberada
    return {
        'liberada': True,
        'ate': ctx.liberada(),
        'rodadas': [{'numero': n, 'nome': ctx.rodada(n).nome} for n in range(1, ctx.liberada_ate + 1)],
        'rodada': numero,
        'variacaoReferencia': ctx.referencia_variacao(),
        'itens': _itens_ranking(bolao, ranking),
        'eliminadosOcultos': len(eliminados_no_ranking(
            bolao, carregar_participantes(bolao), ctx.rodada(numero) if numero else None,
            ate_rodada=ctx.rodada(ctx.liberada_ate))) if bolao.eliminacao_participantes else 0,
    }


# ---------- abas ----------

def regras(bolao):
    return {**serializar_regras(bolao), 'politicaEntrada': bolao.politica_entrada_tardia}


def inicio(bolao):
    """Dashboard público: sem palpites faltantes; líderes só com a tabela liberada."""
    ctx = Contexto(bolao)
    agora = agora_brasilia()
    rodada = ctx.referencia()
    jogos = _por_horario(rodada.jogos) if rodada else []
    ativos = Participacao.query.filter_by(bolao_id=bolao.id, status='ativo').count()
    lideres = None
    if ctx.liberada_ate is not None:
        lideres = _itens_ranking(bolao, ranking_liberado(ctx, ocultar_desistentes=True))[:5]
    return {
        'bolao': {'nome': bolao.nome, 'campeonato': bolao.campeonato.nome, 'ano': bolao.campeonato.ano},
        'tabela': ctx.liberada(),
        'participantesAtivos': ativos,
        'rodada': ({**ctx.resumo_rodada(rodada), 'total': len(ctx.rodadas)} if rodada else None),
        'jogos': [jogo_publico(j, bolao.campeonato_id, agora) for j in jogos],
        'lideres': lideres,
        'variacaoReferencia': ctx.referencia_variacao(),
        'regras': regras(bolao),
    }


def jogos(bolao, numero=None):
    """Mesma agenda da aba Jogos do admin: rodada, horários e jogos atrasados (sem dados de gestão)."""
    ctx = Contexto(bolao)
    atual = ctx.referencia()
    rodada = ctx.rodada(numero) if numero is not None else atual
    if numero is not None and rodada is None:
        return None
    agora = agora_brasilia()
    lista = _por_horario(rodada.jogos) if rodada else []
    datas = [j.data for j in lista if j.data]

    # Atrasados: jogos sem resultado de rodadas anteriores à rodada atual (mesma regra do admin).
    atrasados = []
    if atual:
        for r in ctx.rodadas:
            if ordem_rodada(r) >= ordem_rodada(atual):
                break
            for j in _por_horario(r.jogos):
                if not tem_resultado(j):
                    atrasados.append({**jogo_publico(j, bolao.campeonato_id, agora), 'rodadaNome': r.nome})

    return {
        'agora': agora.isoformat(),
        'rodadas': ctx.lista_rodadas(),
        'rodada': {
            **ctx.resumo_rodada(rodada), 'total': len(ctx.rodadas),
            'atual': bool(atual and rodada.id == atual.id),
            'inicio': min(datas).isoformat() if datas else None,
            'inicioTexto': texto_data(min(datas)) if datas else None,
            'fimTexto': texto_data(max(datas)) if datas else None,
            'semHorario': sum(1 for j in lista if j.data is None),
        } if rodada else None,
        'atual': ctx.numero[atual.id] if atual else None,
        'jogos': [jogo_publico(j, bolao.campeonato_id, agora) for j in lista],
        'atrasados': atrasados,
    }


def palpites(bolao, numero=None):
    """Palpites da rodada: só de rodadas liberadas e, nelas, só dos jogos com resultado."""
    ctx = Contexto(bolao)
    if numero is not None:
        rodada = ctx.rodada(numero)
        if rodada is None:
            return None
    else:
        # Padrão: a última rodada com resultado entre as liberadas (ou a atual, sem nada liberado).
        rodada = (ctx.ultima_com_resultado(ctx.liberada_ate) if ctx.liberada_ate else None) or ctx.referencia()
    if rodada is None:
        return {'rodadas': [], 'rodada': None, 'jogos': [], 'pontosLiberados': False,
                'palpitesLiberados': False, 'tabela': None, 'participantes': 0}
    agora = agora_brasilia()
    jogos_rodada = (Jogo.query.filter_by(rodada_id=rodada.id).options(joinedload(Jogo.resultado))
                    .order_by(*ordem_dos_jogos()).all())
    liberados = ctx.palpites_liberados(rodada)
    revelados = [j for j in jogos_rodada if tem_resultado(j)] if liberados else []
    regras_bolao = regras_do_bolao(bolao)

    pessoas = [p for p in (Participacao.query.filter(Participacao.bolao_id == bolao.id,
                                                     Participacao.status.in_(STATUS_VISIVEIS))
                           .options(joinedload(Participacao.bolao), joinedload(Participacao.rodada_entrada),
                                    joinedload(Participacao.rodada_desistencia))
                           .order_by(Participacao.nome_exibicao, Participacao.id).all())
               if entra_no_ranking_da_rodada(p, rodada)]
    mapa = {}
    if revelados:
        # Filtro no banco: só palpites dos jogos com resultado de rodada liberada são lidos.
        consulta = (Palpite.query.join(Participacao, Participacao.id == Palpite.participacao_id)
                    .filter(Participacao.bolao_id == bolao.id,
                            Palpite.jogo_id.in_([j.id for j in revelados])))
        for p in consulta.all():
            if palpite_elegivel(p):
                mapa[(p.participacao_id, p.jogo_id)] = p

    ids_revelados = {j.id for j in revelados}
    lista_jogos = []
    for numero_jogo, jogo in enumerate(jogos_rodada, 1):
        item = jogo_publico(jogo, bolao.campeonato_id, agora, numero_jogo)
        item['revelado'] = jogo.id in ids_revelados
        if item['revelado']:
            linhas = []
            for pessoa in pessoas:
                p = mapa.get((pessoa.id, jogo.id))
                linha = {'nome': pessoa.nome_exibicao, 'status': pessoa.status, 'ref': referencia(bolao, pessoa)}
                if p is None:
                    linha['situacao'] = 'sem_palpite'
                elif p.situacao != 'valido':
                    linha['situacao'] = p.situacao
                else:
                    linha.update({'situacao': 'valido', 'casa': p.gols_casa, 'fora': p.gols_fora})
                    if p.penaltis_casa is not None and p.penaltis_fora is not None:
                        linha.update({'penaltisCasa': p.penaltis_casa, 'penaltisFora': p.penaltis_fora})
                    if jogo.classico and p.primeiro_gol:
                        linha['primeiroGol'] = p.primeiro_gol
                linha['pontos'] = calcular_pontuacao(p, jogo, jogo.resultado, regras_bolao).total if p else 0
                linhas.append(linha)
            item['palpites'] = linhas
        lista_jogos.append(item)
    return {
        'rodadas': ctx.lista_rodadas(),
        'rodada': ctx.resumo_rodada(rodada),
        'pontosLiberados': ctx.pontos_liberados(rodada),
        'palpitesLiberados': liberados,
        'tabela': ctx.liberada(),
        'participantes': len(pessoas),
        'jogos': lista_jogos,
    }


def participantes(bolao):
    ctx = Contexto(bolao)
    pessoas = (Participacao.query.filter(Participacao.bolao_id == bolao.id,
                                         Participacao.status.in_(STATUS_VISIVEIS))
               .order_by(Participacao.nome_exibicao, Participacao.id).all())
    posicoes = {}
    if ctx.liberada_ate is not None:
        todos = carregar_participantes(bolao)
        geral = ranking_liberado(ctx, ocultar_desistentes=False, todos=todos)
        pontos = {item['participante'].id: item for item in geral}
        sem_desistentes = [item for item in geral if item['participante'].status != 'desistente']
        ordem = {item['participante'].id: i for i, item in enumerate(sem_desistentes, 1)}
        posicoes = {pid: (ordem.get(pid), item) for pid, item in pontos.items()}
    lista = []
    for p in pessoas:
        linha = {'nome': p.nome_exibicao, 'status': p.status, 'ref': referencia(bolao, p)}
        if p.id in posicoes:
            posicao, item = posicoes[p.id]
            linha.update({'posicao': posicao, 'pontos': item['pontos'], 'cravadas': item['cravadas']})
        lista.append(linha)
    return {'tabela': ctx.liberada(), 'participantes': lista}


def participante(bolao, ref):
    """Desempenho de um participante até a rodada liberada: totais, posição e pontos por rodada.

    Não inclui palpites, e-mail, observação, histórico de alterações nem palpites guardados.
    A posição segue a classificação pública (desistentes fora da conta, exceto para o próprio desistente).
    """
    if not ref or not FORMATO_REF.fullmatch(ref):
        return None
    todos = carregar_participantes(bolao)
    pessoa = next((p for p in todos if hmac.compare_digest(referencia(bolao, p), ref)), None)
    if pessoa is None or pessoa.status not in STATUS_VISIVEIS:
        return None
    ctx = Contexto(bolao)
    base = {'ref': ref, 'nome': pessoa.nome_exibicao, 'status': pessoa.status, 'tabela': ctx.liberada()}
    if ctx.liberada_ate is None:
        return {**base, 'liberada': False}

    desistente = pessoa.status == 'desistente'
    geral = ranking_liberado(ctx, ocultar_desistentes=not desistente, todos=todos)
    posicao, item = next(((i, it) for i, it in enumerate(geral, 1) if it['participante'].id == pessoa.id),
                         (None, None))
    universo = todos if desistente else [p for p in todos if p.status != 'desistente']
    linhas = [l for l in evolucao(bolao, universo).get(pessoa.id, [])
              if ctx.numero.get(l['rodada'].id, ctx.liberada_ate + 1) <= ctx.liberada_ate]
    return {
        **base, 'liberada': True,
        'posicao': posicao,
        'variacao': item.get('variacao') if item else None,
        'variacaoReferencia': ctx.referencia_variacao(),
        'pontos': item['pontos'] if item else 0,
        'cravadas': item['cravadas'] if item else 0,
        'acertos': item['acertos_vencedor'] if item else 0,
        'bonus': (item['bonus'] + item['bonus_primeiro_gol']) if item else 0,
        'evolucao': [{
            'numero': ctx.numero[l['rodada'].id], 'rodada': l['rodada'].nome, 'curto': rotulo_curto(l['rodada']),
            'pontos': l['pontos'] if l['participa'] else None, 'cravadas': l['cravadas'],
            'palpites': l['palpites'], 'acumulado': l['acumulado'],
            'posicao': l['posicao'], 'participa': l['participa'],
        } for l in linhas],
    }


def tabela(bolao):
    """Tabela do campeonato (mesma fonte e cache da aba Jogos do admin)."""
    return dados_tabela(bolao.campeonato, publico=True)
