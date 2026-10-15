"""Cadastro, edição, status e desistência de participações.

Regras movidas de routes/admin.py sem mudança de comportamento, para que a tela
atual e a nova interface usem exatamente o mesmo código. Nenhuma função aqui faz
commit: quem chama decide (as rotas fazem rollback quando há erros).
"""
import hmac

from flask import abort, current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

from models import Participacao, Rodada, agora_utc
from services.contexto_bolao import ordem_rodada
from services.gestao_participantes import validar_dados_participante
from services.responsaveis import validar_retirada


def criar(bolao, nome, email, observacao, rodada_ids):
    """Valida e adiciona (sem commit). rodada_ids: valores recebidos para a rodada de entrada."""
    from database import db
    erros = validar_dados_participante(bolao.id, nome, email)
    try:
        rodada_id = int(rodada_ids[0]) if rodada_ids else None
    except (TypeError, ValueError):
        rodada_id = None
    rodada = Rodada.query.filter_by(id=rodada_id, campeonato_id=bolao.campeonato_id).first() if rodada_id else None
    if rodada is None or len(rodada_ids) != 1:
        erros['rodada_entrada_id'] = 'Selecione uma rodada de entrada deste campeonato.'
    if erros:
        return None, erros
    pessoa = Participacao(bolao_id=bolao.id, nome_exibicao=nome, papel='participante', status='ativo',
                          observacao=observacao, email=email, rodada_entrada_id=rodada.id)
    db.session.add(pessoa)
    return pessoa, {}


def editar(bolao, pessoa, nome, email, responsavel, observacao):
    """responsavel: None (não enviado), 'sim' ou 'nao'. observacao None = não enviada."""
    erros = validar_dados_participante(bolao.id, nome, email, pessoa.id)
    if responsavel is not None and responsavel not in {'sim', 'nao'}:
        erros['responsavel'] = 'Selecione Sim ou Não.'
    if responsavel == 'sim' and pessoa.status != 'ativo':
        erros['responsavel'] = 'Reative o participante antes de torná-lo responsável.'
    if erros:
        return erros
    if responsavel == 'nao':
        validar_retirada(pessoa)
        pessoa.papel = 'participante'
    elif responsavel == 'sim':
        pessoa.papel = 'responsavel'
    pessoa.email = email
    pessoa.nome_exibicao = nome
    if observacao is not None:
        pessoa.observacao = observacao.strip() or None
    return {}


def alterar_status(pessoa, acao):
    if pessoa.status == 'desistente':
        abort(409, description='Use a tela de desistência para corrigir ou reativar com revisão dos palpites.')
    if acao == 'remover':
        validar_retirada(pessoa)
        if pessoa.status == 'ativo':
            pessoa.status = 'removido'
            pessoa.saiu_em = agora_utc()
    elif acao == 'reativar':
        # Reativação do registro não concede acesso administrativo implicitamente.
        if pessoa.status != 'ativo':
            pessoa.papel = 'participante'
            pessoa.status = 'ativo'
            pessoa.saiu_em = None
    else:
        abort(400)


# ── Desistência ──────────────────────────────────────────────────────────────

def _assinador():
    return URLSafeTimedSerializer(current_app.secret_key, salt='confirmacao-desistencia-v1')


def erro_rodada_desistencia(pessoa, acao, rodada, quantidade):
    """Mensagem de erro (422) da rodada escolhida, ou None."""
    if acao in {'registrar', 'corrigir'} and (rodada is None or quantidade != 1):
        return 'Selecione uma rodada de desistência deste campeonato.'
    if acao in {'registrar', 'corrigir'} and pessoa.rodada_entrada and (
            ordem_rodada(rodada) < ordem_rodada(pessoa.rodada_entrada)):
        return 'A desistência não pode ser anterior à rodada de entrada.'
    return None


def gerar_confirmacao(plano, autor_id):
    return _assinador().dumps({'autor': autor_id, 'estado': plano.fingerprint})


def confirmacao_valida(token, plano, autor_id):
    """Válida só para o mesmo autor, por 30 minutos e se nada mudou desde a prévia."""
    try:
        payload = _assinador().loads(token or '', max_age=1800)
        return (payload.get('autor') == autor_id and
                hmac.compare_digest(payload.get('estado', ''), plano.fingerprint))
    except (BadSignature, TypeError, AttributeError):
        return False
