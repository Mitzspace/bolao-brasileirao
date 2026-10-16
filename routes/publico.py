"""Área pública: consulta somente leitura por link, sem login.

Segurança:
- Somente GET. Não há nenhuma rota de gravação neste módulo; POST/PUT/DELETE recebem 405.
- Não usa sessão nem login: nada aqui alcança as rotas do admin (/interface/...).
- O acesso é pelo código aleatório do link (bolao.codigo_publico). Código mal formado,
  inexistente ou revogado recebe sempre o mesmo 404 genérico.
- Todo filtro de visibilidade é feito no servidor (services/publico.py).
- Limite de requisições por IP e cache curto para proteger a instância gratuita.
"""
from flask import Blueprint, abort, current_app, jsonify, render_template, request, url_for

from extensions import limiter
from services import cache_publico
from services.assets_vite import assets_da_entrada
from services import publico as dados_publicos

publico = Blueprint('publico', __name__, url_prefix='/publico')

# Folgado para várias pessoas na mesma rede (4G/Wi-Fi compartilham IP),
# baixo o bastante para um robô não derrubar a instância gratuita.
limiter.limit('90 per minute;1500 per hour')(publico)

CABECALHOS = {
    'X-Robots-Tag': 'noindex, nofollow',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
}
MENSAGENS = {404: 'Link inválido ou desativado.', 429: 'Muitos acessos em pouco tempo. Aguarde um instante.',
             500: 'Não foi possível carregar agora. Tente novamente em instantes.'}


def _bolao(codigo):
    bolao = dados_publicos.bolao_do_codigo(codigo)
    if bolao is None:
        abort(404)
    return bolao


def _numero():
    """Número da rodada (?rodada=N). Ausente: None. Presente e inválido: 404."""
    if 'rodada' not in request.args:
        return None
    numero = request.args.get('rodada', type=int)
    if numero is None:
        abort(404)
    return numero


def _resposta(corpo, sem_dados='Rodada não encontrada.'):
    if corpo is None:
        resposta = jsonify({'erro': sem_dados})
        resposta.status_code = 404
        resposta.headers.update(CABECALHOS)
        return resposta
    resposta = jsonify(corpo)
    resposta.headers['Cache-Control'] = 'public, max-age=15'
    resposta.headers.update(CABECALHOS)
    return resposta


def _servir(codigo, nome, gerar, *chave, sem_dados='Rodada não encontrada.'):
    bolao = _bolao(codigo)
    return _resposta(cache_publico.obter((bolao.id, nome, *chave), lambda: gerar(bolao)), sem_dados)


@publico.errorhandler(404)
@publico.errorhandler(429)
@publico.errorhandler(500)
def _erro(e):
    codigo = getattr(e, 'code', 500) or 500
    if codigo == 500:
        current_app.logger.exception('Erro na área pública')
    mensagem = MENSAGENS.get(codigo, MENSAGENS[500])
    if '/api/' in request.path:
        resposta = jsonify({'erro': mensagem})
    else:
        resposta = current_app.make_response(render_template(
            'erro.html', codigo=codigo, titulo=mensagem, sem_link=True,
            texto='Confira o link com quem organiza o bolão.' if codigo == 404 else 'Tente novamente em instantes.'))
    resposta.status_code = codigo
    resposta.headers.update(CABECALHOS)
    return resposta


def _assets():
    return assets_da_entrada('src/publico/main.tsx')


@publico.get('/<codigo>')
def pagina(codigo):
    bolao = _bolao(codigo)
    dados = {
        'bolao': {'nome': bolao.nome, 'campeonato': bolao.campeonato.nome, 'ano': bolao.campeonato.ano},
        'apiBase': url_for('publico.pagina', codigo=codigo) + '/api',
    }
    resposta = current_app.make_response(render_template('publico.html', dados=dados, assets=_assets()))
    resposta.headers['Cache-Control'] = 'no-cache'
    resposta.headers.update(CABECALHOS)
    return resposta


@publico.get('/<codigo>/api/inicio')
def inicio(codigo):
    return _servir(codigo, 'inicio', dados_publicos.inicio)


@publico.get('/<codigo>/api/classificacao')
def classificacao(codigo):
    numero = _numero()
    ocultar = request.args.get('desistentes') != 'mostrar'  # padrão: ocultar desistentes
    return _servir(codigo, 'classificacao', lambda b: dados_publicos.classificacao(b, numero, ocultar),
                   numero, ocultar, sem_dados='Esta rodada ainda não foi liberada na classificação.')


@publico.get('/<codigo>/api/jogos')
def jogos(codigo):
    numero = _numero()
    return _servir(codigo, 'jogos', lambda b: dados_publicos.jogos(b, numero), numero)


@publico.get('/<codigo>/api/palpites')
def palpites(codigo):
    numero = _numero()
    return _servir(codigo, 'palpites', lambda b: dados_publicos.palpites(b, numero), numero)


@publico.get('/<codigo>/api/participantes')
def participantes(codigo):
    return _servir(codigo, 'participantes', dados_publicos.participantes)
