"""Aba Configurações: perfil da conta, senha e responsáveis do bolão."""
from flask import flash, jsonify, request
from flask_login import current_user

from extensions import limiter
from models import Participacao
from routes.api import api, erro, requer_gestao
from services.conta import alterar_email, alterar_nome, alterar_senha
from services.contexto_bolao import bolao_atual
from services.responsaveis import adicionar_responsavel, bloquear_bolao, remover_responsavel


def _corpo():
    dados = request.get_json(silent=True)
    return dados if isinstance(dados, dict) else {}


def _texto(c, chave):
    valor = c.get(chave)
    return valor if isinstance(valor, str) else ''


def _executar(acao, mensagem, avisar_na_recarga=False):
    try:
        acao()
    except ValueError as e:
        return erro(400, str(e))
    if avisar_na_recarga:
        # A interface recarrega para atualizar nome/e-mail no menu; o aviso aparece depois.
        flash(mensagem, 'success')
    return jsonify({'mensagem': mensagem})


@api.put('/perfil')
@requer_gestao(precisa_bolao=False)
def salvar_perfil():
    c = _corpo()
    return _executar(lambda: alterar_nome(current_user, _texto(c, 'nome')), 'Perfil atualizado.', True)


# Exigem a senha atual: limite próprio contra tentativa de adivinhar a senha.
@api.put('/perfil/email')
@limiter.limit('10 per hour')
@requer_gestao(precisa_bolao=False)
def salvar_email():
    c = _corpo()
    return _executar(lambda: alterar_email(current_user, _texto(c, 'email'), _texto(c, 'senhaAtual')),
                     'E-mail de acesso alterado. Use o novo e-mail no próximo login.', True)


@api.put('/perfil/senha')
@limiter.limit('10 per hour')
@requer_gestao(precisa_bolao=False)
def salvar_senha():
    c = _corpo()
    return _executar(lambda: alterar_senha(current_user, _texto(c, 'senhaAtual'), _texto(c, 'novaSenha'),
                                           _texto(c, 'confirmacao')), 'Senha alterada.')


def _serializar_responsavel(p):
    conta = p.usuario
    return {'id': p.id, 'nome': p.nome_exibicao, 'email': conta.email if conta else (p.email or ''),
            'souEu': p.usuario_id == current_user.id,
            'semAcesso': not conta or not conta.conta_ativa or not conta.senha}


@api.get('/responsaveis')
@requer_gestao()
def listar_responsaveis():
    bolao = bolao_atual()
    pessoas = Participacao.query.filter_by(bolao_id=bolao.id, papel='responsavel', status='ativo').all()
    sem_conta = (Participacao.query.filter_by(bolao_id=bolao.id, usuario_id=None, status='ativo')
                 .order_by(Participacao.nome_exibicao).all())
    return jsonify({
        'responsaveis': [_serializar_responsavel(p) for p in sorted(pessoas, key=lambda p: (not p.usuario_id == current_user.id, p.nome_exibicao.casefold()))],
        'participantesSemConta': [{'id': p.id, 'nome': p.nome_exibicao} for p in sem_conta],
    })


@api.post('/responsaveis')
@requer_gestao()
def novo_responsavel():
    c = _corpo()
    bolao = bolao_atual()
    selecionada = c.get('participacaoId')
    if selecionada is not None and (isinstance(selecionada, bool) or not isinstance(selecionada, (int, str))):
        return erro(400)
    bloquear_bolao(bolao.id)
    adicionar_responsavel(bolao, _texto(c, 'email'), _texto(c, 'nome'), _texto(c, 'senha'),
                          '' if selecionada in (None, '') else str(selecionada))
    return jsonify({'mensagem': 'Responsável adicionado a este bolão. Os demais bolões não foram alterados.'}), 201


@api.delete('/responsaveis/<int:id>')
@requer_gestao()
def retirar_responsavel(id):
    bolao = bolao_atual()
    bloquear_bolao(bolao.id)
    propria = remover_responsavel(bolao, id)
    return jsonify({'mensagem': 'Acesso de responsável removido; participação e histórico preservados.',
                    'logout': propria})
