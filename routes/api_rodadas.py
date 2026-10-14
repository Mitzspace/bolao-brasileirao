"""Aba Rodadas: jogos e resultados de cada rodada (cadastro, edição, resultado, encerramento)."""
from datetime import datetime

from flask import jsonify, request, url_for
from sqlalchemy import func

from database import db
from models import Jogo, Palpite, Participacao, Rodada
from routes.api import api, erro, requer_gestao
from routes.api_serializacao import serializar_item_ranking, serializar_jogo
from services.contexto_bolao import bolao_atual, opcoes_rodadas, validar_rodada
from services.elegibilidade import participa_na_rodada
from services.pontuacao import normalizar_nome_jogador
from services.estado_rodadas import estados_das_rodadas
from services.gestao_jogos import criar_jogo, definir_encerrado, editar_jogo, excluir_jogo, lancar_resultado
from services.ranking import calcular_ranking
from services.resumo_boloes import rodadas_de_referencia


def _jogo_do_bolao(id):
    jogo = Jogo.query.get_or_404(id)
    validar_rodada(jogo.rodada)  # 404 se for de outro campeonato
    return jogo


def _rodada_do_bolao(id):
    rodada = Rodada.query.get_or_404(id)
    validar_rodada(rodada)
    return rodada


def sugestoes_primeiro_gol(jogo, bolao_id):
    """Nomes de primeiro gol palpitados no clássico (agrupados como a pontuação compara)."""
    grupos = {}
    for p in jogo.palpites:
        if p.participacao.bolao_id != bolao_id or p.excluido_por_desistencia or not (p.primeiro_gol or '').strip():
            continue
        chave = normalizar_nome_jogador(p.primeiro_gol)
        nome, total = grupos.get(chave, (p.primeiro_gol.strip(), 0))
        grupos[chave] = (nome, total + 1)
    return [{'nome': nome, 'palpites': total} for nome, total in sorted(grupos.values(), key=lambda x: (-x[1], x[0]))]


def _detalhar(jogo, campeonato_id, palpites, bolao_id):
    base = serializar_jogo(jogo, campeonato_id)
    return {
        **base,
        'rodadaId': jogo.rodada_id,
        'encerrado': bool(jogo.encerrado),
        'primeiroGol': jogo.resultado.primeiro_gol_real if jogo.resultado else None,
        'dataInput': jogo.data.strftime('%Y-%m-%dT%H:%M') if jogo.data else '',
        'palpites': palpites.get(jogo.id, 0),
        'podeExcluir': palpites.get(jogo.id, 0) == 0 and not jogo.palpites,
        'sugestoesPrimeiroGol': sugestoes_primeiro_gol(jogo, bolao_id) if jogo.classico else [],
        'links': {'editarAntigo': url_for('admin.editar_jogo', id=jogo.id)},
    }


@api.get('/rodadas')
@requer_gestao()
def gestao_rodadas():
    bolao = bolao_atual()
    rodadas = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    referencia = rodadas_de_referencia({bolao.campeonato_id})[bolao.campeonato_id]['rodada']
    rodada = referencia
    if request.args.get('rodada_id'):
        rodada = next((r for r in rodadas if r.id == request.args.get('rodada_id', type=int)), None)
        if rodada is None:
            return erro(404, 'Rodada não encontrada neste bolão.')
    estados = estados_das_rodadas(bolao, rodadas)
    jogos, palpites, participantes = [], {}, 0
    if rodada:
        jogos = sorted(rodada.jogos, key=lambda j: (j.data is None, j.data or datetime.min, j.id))
        palpites = dict(db.session.query(Palpite.jogo_id, func.count(Palpite.id))
                        .join(Participacao, Participacao.id == Palpite.participacao_id)
                        .filter(Participacao.bolao_id == bolao.id, Palpite.excluido_por_desistencia.is_(False),
                                Palpite.jogo_id.in_([j.id for j in jogos]))
                        .group_by(Palpite.jogo_id).all()) if jogos else {}
        participantes = sum(1 for p in Participacao.query.filter_by(bolao_id=bolao.id).all()
                            if participa_na_rodada(p, rodada))
    return jsonify({
        'rodadas': [{'id': r.id, 'numero': i, 'nome': r.nome, **estados[r.id]} for i, r in enumerate(rodadas, 1)],
        'rodadaAtualId': referencia.id if referencia else None,
        'rodada': {
            'id': rodada.id, 'nome': rodada.nome, **estados[rodada.id],
            'participantes': participantes,
            'links': {'palpites': url_for('admin.gerenciar_palpites', rodada_id=rodada.id),
                      'grade': url_for('participante.ver_grade_palpites', id=rodada.id)},
        } if rodada else None,
        'jogos': [_detalhar(j, bolao.campeonato_id, palpites, bolao.id) for j in jogos],
    })


@api.get('/rodadas/<int:id>/classificacao')
@requer_gestao()
def classificacao_rodada(id):
    rodada = _rodada_do_bolao(id)
    ranking = calcular_ranking(bolao_atual(), rodada)
    for posicao, item in enumerate(ranking, 1):
        item['posicao'] = posicao
    return jsonify({'rodada': rodada.nome, 'ranking': [serializar_item_ranking(i) for i in ranking]})


def _corpo():
    return request.get_json(silent=True) or {}


@api.post('/jogos')
@requer_gestao()
def novo_jogo():
    c = _corpo()
    try:
        jogo = criar_jogo(c.get('casa'), c.get('fora'), c.get('rodadaId'), c.get('data'), c.get('classico'))
    except ValueError as e:
        return erro(400, str(e))
    return jsonify({'mensagem': f'Jogo {jogo.time_casa} x {jogo.time_fora} cadastrado!', 'id': jogo.id}), 201


@api.put('/jogos/<int:id>')
@requer_gestao()
def salvar_jogo(id):
    jogo = _jogo_do_bolao(id)
    c = _corpo()
    try:
        editar_jogo(jogo, c.get('casa'), c.get('fora'), c.get('rodadaId'), c.get('data'), c.get('classico'))
    except ValueError as e:
        return erro(400, str(e))
    return jsonify({'mensagem': f'Jogo {jogo.time_casa} x {jogo.time_fora} atualizado!'})


@api.post('/jogos/<int:id>/resultado')
@requer_gestao()
def salvar_resultado(id):
    jogo = _jogo_do_bolao(id)
    c = _corpo()
    try:
        lancar_resultado(jogo, c.get('golsCasa'), c.get('golsFora'), c.get('primeiroGol') if jogo.classico else None)
    except ValueError as e:
        return erro(400, str(e))
    return jsonify({'mensagem': 'Resultado salvo!'})


@api.post('/jogos/<int:id>/encerrado')
@requer_gestao()
def alterar_encerrado(id):
    jogo = _jogo_do_bolao(id)
    encerrado = bool(_corpo().get('encerrado'))
    definir_encerrado(jogo, encerrado)
    acao = 'encerrado para palpites' if encerrado else 'reaberto para palpites'
    return jsonify({'mensagem': f'Jogo {jogo.time_casa} x {jogo.time_fora} {acao}.'})


@api.delete('/jogos/<int:id>')
@requer_gestao()
def remover_jogo(id):
    jogo = _jogo_do_bolao(id)
    try:
        excluir_jogo(jogo)
    except ValueError as e:
        return erro(409, str(e))
    return jsonify({'mensagem': 'Jogo excluído.'})
