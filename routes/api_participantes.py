"""Aba Participantes da nova interface (mesmas regras da tela atual de participantes)."""
from flask import jsonify, request
from flask_login import current_user
from sqlalchemy.orm import joinedload

from database import db
from models import Jogo, Palpite, Participacao, ParticipacaoLog
from routes.api import api, erro, requer_gestao
from services.contexto_bolao import bolao_atual, opcoes_rodadas
from services.desistencias import aplicar, historico_visivel, preparar
from services.elegibilidade import REGRA_DESISTENCIA
from services.evolucao_ranking import evolucao, rotulo_curto
from services.gestao_participantes import normalizar_nome, totais_participantes
from services.participacoes import (alterar_status, confirmacao_valida, criar, editar,
                                    erro_rodada_desistencia, gerar_confirmacao)
from services.ranking import carregar_participantes, ranking_com_variacao
from services.responsaveis import bloquear_bolao
from services.resumo_boloes import rodadas_de_referencia

PRIORIDADE_STATUS = {'ativo': 0, 'desistente': 1, 'saiu': 2, 'removido': 3}


def _texto(dados, campo):
    valor = dados.get(campo)
    return valor.strip() if isinstance(valor, str) else ''


def _pessoa(id):
    return Participacao.query.filter_by(id=id, bolao_id=bolao_atual().id).populate_existing().first_or_404()


def _rodada_padrao(bolao, rodadas):
    referencia = rodadas_de_referencia({bolao.campeonato_id})[bolao.campeonato_id]['rodada']
    return referencia or (rodadas[0] if rodadas else None)


def _serializar_palpite(p):
    return {'id': p.id, 'rodada': p.jogo.rodada.nome, 'jogo': f'{p.jogo.time_casa} × {p.jogo.time_fora}',
            'palpite': f'{p.gols_casa} × {p.gols_fora}', 'primeiroGol': p.primeiro_gol or '',
            'jaGuardado': bool(p.excluido_por_desistencia)}


@api.get('/participantes')
@requer_gestao()
def listar_participantes():
    bolao = bolao_atual()
    pessoas = (Participacao.query.filter_by(bolao_id=bolao.id)
               .options(joinedload(Participacao.rodada_entrada), joinedload(Participacao.rodada_desistencia)).all())
    pessoas.sort(key=lambda p: (PRIORIDADE_STATUS.get(p.status, 4), normalizar_nome(p.nome_exibicao), p.id))
    totais = totais_participantes(bolao.id, pessoas)
    ranking, ultima = ranking_com_variacao(bolao)
    posicoes = {i['participante'].id: i for i in ranking}
    nomes = {}
    for p in pessoas:
        nomes.setdefault(normalizar_nome(p.nome_exibicao), []).append(p.id)
    duplicados = {id for ids in nomes.values() if len(ids) > 1 for id in ids}
    rodadas = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    padrao = _rodada_padrao(bolao, rodadas)

    def serializar(p):
        rank = posicoes.get(p.id, {})
        return {
            'id': p.id, 'nome': p.nome_exibicao, 'email': p.email or '', 'observacao': p.observacao or '',
            'status': p.status, 'responsavel': p.papel == 'responsavel', 'temConta': bool(p.usuario_id),
            'rodadaEntrada': {'id': p.rodada_entrada.id, 'nome': p.rodada_entrada.nome} if p.rodada_entrada else None,
            'rodadaDesistencia': ({'id': p.rodada_desistencia.id, 'nome': p.rodada_desistencia.nome}
                                  if p.rodada_desistencia else None),
            'motivoDesistencia': p.motivo_desistencia or '',
            'pontos': totais[p.id]['pontos'], 'palpites': totais[p.id]['palpites'],
            'cravadas': rank.get('cravadas', 0), 'posicao': rank.get('posicao'), 'variacao': rank.get('variacao'),
            'duplicado': p.id in duplicados, 'souEu': p.usuario_id == current_user.id,
        }

    return jsonify({
        'participantes': [serializar(p) for p in pessoas],
        'contagens': {'todos': len(pessoas), 'ativos': sum(p.status == 'ativo' for p in pessoas),
                      'desistentes': sum(p.status == 'desistente' for p in pessoas)},
        'rodadas': [{'id': r.id, 'nome': r.nome} for r in rodadas],
        'rodadaPadraoId': padrao.id if padrao else None,
        'politicaEntrada': bolao.politica_entrada_tardia,
        'regraDesistencia': REGRA_DESISTENCIA,
        'variacaoReferencia': ultima.nome if ultima else None,
    })


@api.get('/participantes/<int:id>')
@requer_gestao()
def detalhe_participante(id):
    bolao = bolao_atual()
    pessoa = _pessoa(id)
    todos = carregar_participantes(bolao)
    linhas = evolucao(bolao, todos).get(pessoa.id, [])
    rodadas = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    logs = ParticipacaoLog.query.filter_by(participacao_id=id).order_by(ParticipacaoLog.id.desc()).all()
    guardados = (Palpite.query.filter_by(participacao_id=id, excluido_por_desistencia=True)
                 .join(Jogo).order_by(Jogo.rodada_id, Jogo.id).all())
    return jsonify({
        'evolucao': [{
            'rodadaId': l['rodada'].id, 'rodada': l['rodada'].nome, 'curto': rotulo_curto(l['rodada']),
            'pontos': l['pontos'] if l['participa'] else None, 'cravadas': l['cravadas'],
            'palpites': l['palpites'], 'acumulado': l['acumulado'],
            'posicao': l['posicao'], 'participa': l['participa'],
        } for l in linhas],
        'historico': historico_visivel(logs, rodadas),
        'guardados': [_serializar_palpite(p) for p in guardados],
    })


@api.post('/participantes')
@requer_gestao()
def criar_participante():
    bolao = bolao_atual()
    dados = request.get_json(silent=True) or {}
    bloquear_bolao(bolao.id)
    rodada = dados.get('rodadaEntradaId')
    pessoa, erros = criar(bolao, _texto(dados, 'nome'), _texto(dados, 'email').lower() or None,
                          _texto(dados, 'observacao') or None, [rodada] if rodada not in (None, '') else [])
    if erros:
        db.session.rollback()
        return erro(422, 'Confira os campos destacados.', erros=erros)
    db.session.commit()
    return jsonify({'id': pessoa.id, 'mensagem': 'Participante cadastrado sem conta de acesso.'}), 201


@api.put('/participantes/<int:id>')
@requer_gestao()
def editar_participante(id):
    bolao = bolao_atual()
    dados = request.get_json(silent=True) or {}
    bloquear_bolao(bolao.id)
    pessoa = _pessoa(id)
    responsavel = dados.get('responsavel')
    if isinstance(responsavel, bool):
        responsavel = 'sim' if responsavel else 'nao'
    observacao = dados.get('observacao') if isinstance(dados.get('observacao'), str) else None
    email = _texto(dados, 'email').lower() if 'email' in dados else (pessoa.email or '')
    erros = editar(bolao, pessoa, _texto(dados, 'nome'), email or None, responsavel, observacao)
    if erros:
        db.session.rollback()
        return erro(422, 'Confira os campos destacados.', erros=erros)
    db.session.commit()
    return jsonify({'mensagem': 'Participante atualizado somente neste bolão.'})


@api.post('/participantes/<int:id>/status')
@requer_gestao()
def status_participante(id):
    bloquear_bolao(bolao_atual().id)
    pessoa = _pessoa(id)
    alterar_status(pessoa, (request.get_json(silent=True) or {}).get('acao'))
    propria_remocao = pessoa.usuario_id == current_user.id and pessoa.status != 'ativo'
    db.session.commit()
    return jsonify({'mensagem': 'Status atualizado; palpites, pontos e histórico foram preservados.',
                    'logout': propria_remocao})


@api.post('/participantes/<int:id>/desistencia')
@requer_gestao()
def desistencia_participante(id):
    """Sem `confirmar`: só a prévia (nada é gravado). Com `confirmar` e o token da prévia: aplica."""
    bolao = bolao_atual()
    dados = request.get_json(silent=True) or {}
    bloquear_bolao(bolao.id)
    pessoa = _pessoa(id)
    acao = dados.get('acao') or ('corrigir' if pessoa.status == 'desistente' else 'registrar')
    rodadas = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    rodada_id = dados.get('rodadaId')
    rodada = next((r for r in rodadas if r.id == rodada_id), None)
    motivo = _texto(dados, 'motivo')
    mensagem = erro_rodada_desistencia(pessoa, acao, rodada, 1 if rodada_id not in (None, '') else 0)
    if mensagem:
        db.session.rollback()
        return erro(422, mensagem)
    plano = preparar(pessoa, acao, rodada, motivo)
    if dados.get('confirmar'):
        restaurar = dados.get('restaurar')
        if not confirmacao_valida(dados.get('token'), plano, current_user.id):
            db.session.rollback()
            return erro(409, 'A prévia expirou ou os dados mudaram. Confira a lista atualizada e confirme novamente.')
        if plano.restauraveis and restaurar not in {'sim', 'nao'}:
            db.session.rollback()
            return erro(422, 'Escolha se os palpites guardados devem voltar a valer.')
        aplicar(pessoa, plano, current_user.id, restaurar == 'sim')
        return jsonify({'mensagem': 'Participação atualizada. Histórico preservado e pontuação recalculada '
                                    'pelas regras e resultados oficiais.',
                        'logout': pessoa.usuario_id == current_user.id and pessoa.status != 'ativo'})
    token = gerar_confirmacao(plano, current_user.id)
    previa = {
        'acao': acao, 'rodada': plano.rodada.nome if plano.rodada else None, 'motivo': motivo,
        'posteriores': [_serializar_palpite(p) for p in plano.posteriores],
        'restauraveis': [_serializar_palpite(p) for p in plano.restauraveis],
    }
    db.session.rollback()  # A prévia nunca grava dados, nem mantém bloqueio.
    return jsonify({'previa': previa, 'token': token})
