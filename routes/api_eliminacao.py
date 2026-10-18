"""Configuração de eliminação e metadados da classificação."""
from flask import current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from database import db
from models import Bolao, CorteEliminacao, Rodada
from routes.api import api, erro, requer_gestao
from services.contexto_bolao import bolao_atual, opcoes_rodadas, ordem_rodada
from services.eliminacao import eliminados_no_ranking
from services.ranking import carregar_participantes
from services.responsaveis import bloquear_bolao


@api.get('/eliminacao')
@requer_gestao()
def configuracao_eliminacao():
    bolao = bolao_atual()
    cortes = sorted(bolao.cortes_eliminacao, key=lambda c: ordem_rodada(c.rodada))
    return jsonify({
        'eliminacaoParticipantes': bool(bolao.eliminacao_participantes),
        'cortes': [{'id': c.id, 'rodadaId': c.rodada_id, 'rodadaNome': c.rodada.nome,
                    'classificados': c.classificados} for c in cortes],
        'rodadas': [{'id': r.id, 'nome': r.nome} for r, _ in opcoes_rodadas(bolao.campeonato_id)],
    })


@api.route('/eliminacao', methods=['PUT', 'POST'])
@requer_gestao()
def salvar_eliminacao():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict) or not isinstance(dados.get('eliminacaoParticipantes'), bool):
        return erro(400, 'Informe se a eliminação está ligada ou desligada.')
    bolao = bolao_atual()
    bloquear_bolao(bolao.id)
    bolao.eliminacao_participantes = dados['eliminacaoParticipantes']
    db.session.commit()
    return jsonify({'mensagem': 'Configuração de eliminação salva.'})


@api.post('/eliminacao/cortes')
@requer_gestao()
def adicionar_corte():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict) or any(
            type(dados.get(c)) is not int or not 1 <= dados[c] <= 2147483647
            for c in ('rodadaId', 'classificados')):
        return erro(400, 'Informe uma rodada e um número inteiro de classificados maior ou igual a 1.')
    bolao = bolao_atual()
    bloquear_bolao(bolao.id)
    rodada = Rodada.query.filter_by(id=dados['rodadaId'], campeonato_id=bolao.campeonato_id).first()
    if rodada is None:
        return erro(400, 'Selecione uma rodada deste campeonato.')
    cortes = CorteEliminacao.query.filter_by(bolao_id=bolao.id).all()
    if any(c.rodada_id == rodada.id for c in cortes):
        return erro(400, 'Já existe um corte nesta rodada.')
    ordem, n = ordem_rodada(rodada), dados['classificados']
    if any((ordem_rodada(c.rodada) < ordem and c.classificados <= n)
           or (ordem_rodada(c.rodada) > ordem and c.classificados >= n) for c in cortes):
        return erro(400, 'Os cortes posteriores devem ter menos classificados que os anteriores.')
    db.session.add(CorteEliminacao(bolao=bolao, rodada=rodada, classificados=n))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return erro(400, 'Já existe um corte nesta rodada.')
    return jsonify({'mensagem': 'Corte de eliminação adicionado.'}), 201


@api.delete('/eliminacao/cortes/<int:id>')
@requer_gestao()
def remover_corte(id):
    bolao = bolao_atual()
    bloquear_bolao(bolao.id)
    corte = CorteEliminacao.query.filter_by(id=id, bolao_id=bolao.id).first()
    if corte is None:
        return erro(404)
    db.session.delete(corte)
    db.session.commit()
    return jsonify({'mensagem': 'Corte de eliminação removido.'})


@api.after_request
def incluir_contagem_eliminados(resposta):
    # Mantém a extensão no módulo da funcionalidade, sem alterar api_boloes.
    # A rota original já validou acesso ao bolão e a rodada solicitada.
    if request.endpoint != 'api.classificacao_bolao' or resposta.status_code != 200:
        return resposta
    dados = resposta.get_json()
    bolao = db.session.get(Bolao, dados['bolao']['id'])
    rodada = db.session.get(Rodada, dados['rodadaId']) if dados['rodadaId'] else None
    dados['eliminadosOcultos'] = (len(eliminados_no_ranking(bolao, carregar_participantes(bolao), rodada))
                                  if bolao.eliminacao_participantes else 0)
    resposta.set_data(current_app.json.dumps(dados))
    return resposta
