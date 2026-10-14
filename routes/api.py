"""API JSON da nova interface.

Regras desta camada:
- só responsáveis acessam (mesma regra das telas atuais de gestão);
- o bolão vem da sessão já validada por services.contexto_bolao;
- cálculos e gravações reutilizam os serviços existentes, nunca lógica duplicada no React;
- erros sempre em JSON ({"erro": "..."}), inclusive CSRF e limite de requisições.
"""
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

from extensions import limiter
from services.acesso import pode_acessar_gestao
from services.contexto_bolao import bolao_atual, responsavel_atual

api = Blueprint('api', __name__, url_prefix='/interface/api')

# A interface faz várias chamadas por tela; o limite padrão (50/hora por IP)
# vale para as telas antigas e bloquearia o uso normal da API.
limiter.limit('1500 per hour')(api)

MENSAGENS = {
    400: 'Requisição inválida.',
    401: 'Sua sessão expirou. Entre novamente.',
    403: 'Acesso não permitido.',
    404: 'Registro não encontrado.',
    405: 'Operação não permitida.',
    409: 'Selecione um bolão para continuar.',
    429: 'Muitas requisições em pouco tempo. Aguarde alguns minutos.',
}


def erro(status, mensagem=None, **extra):
    corpo = {'erro': mensagem or MENSAGENS.get(status, 'Erro inesperado.'), **extra}
    return jsonify(corpo), status


@api.errorhandler(CSRFError)
def erro_csrf(e):
    return erro(403, 'Sessão de segurança expirada. Recarregue a página e tente novamente.')


@api.errorhandler(HTTPException)
def erro_http(e):
    # Mensagens de abort(…, 'texto') definidas pelos serviços são preservadas.
    padrao = type(e).description
    mensagem = e.description if e.description and e.description != padrao else None
    return erro(e.code or 500, mensagem)


@api.errorhandler(Exception)
def erro_inesperado(e):
    current_app.logger.exception('Erro na API da interface')
    from database import db
    db.session.rollback()
    return erro(500, 'Erro inesperado no servidor. Nada foi alterado.')


@api.record_once
def _rotas_inexistentes_em_json(state):
    """404/405 de URLs da API não chegam ao blueprint; respondem JSON mesmo assim."""
    def tratar(e):
        if request.path.startswith(api.url_prefix + '/'):
            return erro(e.code)
        return e
    state.app.register_error_handler(404, tratar)
    state.app.register_error_handler(405, tratar)


def requer_gestao(precisa_bolao=True):
    """Equivalente ao admin_required das telas atuais, com respostas JSON."""
    def decorador(f):
        @wraps(f)
        def interno(*args, **kwargs):
            if not current_user.is_authenticated:
                return erro(401)
            if not pode_acessar_gestao(current_user):
                return erro(403)
            if precisa_bolao:
                if bolao_atual() is None:
                    return erro(409)
                if not responsavel_atual():
                    return erro(403)
            return f(*args, **kwargs)
        return interno
    return decorador


def serializar_bolao(bolao):
    return {
        'id': bolao.id, 'nome': bolao.nome, 'chave': bolao.chave,
        'campeonato': bolao.campeonato.nome, 'ano': bolao.campeonato.ano,
        'campeonatoId': bolao.campeonato_id,
    }


@api.get('/contexto')
@requer_gestao(precisa_bolao=False)
def contexto():
    bolao = bolao_atual() if responsavel_atual() else None
    return jsonify({
        'usuario': {'id': current_user.id, 'nome': current_user.nome, 'email': current_user.email,
                    'adminGlobal': bool(current_user.admin_global)},
        'bolao': serializar_bolao(bolao) if bolao else None,
    })
