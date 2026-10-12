"""Consulta da gestão de participantes, sem alterar a fórmula de pontuação."""
import unicodedata

from flask import abort, render_template, request
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database import db
from models import BonusRodada, Jogo, Palpite, Participacao
from services.contexto_bolao import bolao_atual, opcoes_rodadas
from services.pontuacao import calcular_pontuacao
from services.resumo_boloes import rodadas_de_referencia
from services.elegibilidade import palpite_elegivel, dentro_do_periodo


def normalizar_nome(nome):
    sem_acentos = ''.join(c for c in unicodedata.normalize('NFKD', nome)
                          if not unicodedata.combining(c))
    return ' '.join(sem_acentos.casefold().split())


def homonimos(bolao_id, nome, ignorar_id=None):
    chave = normalizar_nome(nome)
    return [p for p in Participacao.query.filter_by(bolao_id=bolao_id).all()
            if p.id != ignorar_id and normalizar_nome(p.nome_exibicao) == chave]


def totais_participantes(bolao_id, pessoas):
    # Contagem inclui os guardados; pontos consideram apenas os elegíveis.
    totais = {p.id: {'pontos': 0, 'palpites': 0} for p in pessoas}
    palpites = (Palpite.query.join(Participacao).filter(Participacao.bolao_id == bolao_id)
                .options(joinedload(Palpite.jogo).joinedload(Jogo.resultado)).all())
    for palpite in palpites:
        total = totais[palpite.participacao_id]
        total['palpites'] += 1
        if palpite_elegivel(palpite):
            total['pontos'] += calcular_pontuacao(palpite, palpite.jogo, palpite.jogo.resultado).total
    for bonus in (BonusRodada.query.join(Participacao).filter(Participacao.bolao_id == bolao_id)
                  .options(joinedload(BonusRodada.rodada)).all()):
        if dentro_do_periodo(bonus.participacao, bonus.rodada):
            totais[bonus.participacao_id]['pontos'] += bonus.pontos
    return totais


def tela_participantes(*, erros=None, dados=None, edicao_id=None, status_http=200):
    bolao = bolao_atual()
    filtro = request.values.get('filtro', 'todos')
    if filtro not in {'todos', 'ativos', 'desistentes'}:
        abort(400, description='Filtro de participantes inválido.')
    pessoas = (Participacao.query.filter_by(bolao_id=bolao.id)
        .options(joinedload(Participacao.rodada_entrada), joinedload(Participacao.rodada_desistencia)).all())
    prioridades = {'ativo': 0, 'desistente': 1, 'saiu': 2, 'removido': 3}
    pessoas.sort(key=lambda p: (prioridades.get(p.status, 4), normalizar_nome(p.nome_exibicao), p.id))
    totais = totais_participantes(bolao.id, pessoas)
    nomes = {}
    for pessoa in pessoas:
        nomes.setdefault(normalizar_nome(pessoa.nome_exibicao), []).append(pessoa.id)
    duplicados = {id for ids in nomes.values() if len(ids) > 1 for id in ids}
    contagens = {'todos': len(pessoas), 'ativos': sum(p.status == 'ativo' for p in pessoas),
                'desistentes': sum(p.status == 'desistente' for p in pessoas)}
    visiveis = [p for p in pessoas if filtro == 'todos' or p.status == (
        'ativo' if filtro == 'ativos' else 'desistente')]
    rodadas = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    referencia = rodadas_de_referencia({bolao.campeonato_id})[bolao.campeonato_id]['rodada']
    padrao = referencia or (rodadas[0] if rodadas else None)
    novo = dados if dados is not None and edicao_id is None else {
        'rodada_entrada_id': str(padrao.id) if padrao else ''}
    return render_template('participacoes_gestao.html', participacoes=visiveis, totais=totais,
        filtro=filtro, contagens=contagens, duplicados=duplicados, rodadas=rodadas,
        novo=novo, edicao=dados or {}, edicao_id=edicao_id, erros=erros or {}), status_http
