"""Entrada do sistema: a interface React (login, gestão e escolha do bolão)."""
from flask import Blueprint, abort, current_app, g, get_flashed_messages, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf

from services.acesso import pode_acessar_gestao
from services.contexto_bolao import bolao_atual, lembrar_bolao

interface = Blueprint('interface', __name__, url_prefix='/interface')
VIEWS = {'dashboard', 'jogos', 'palpites', 'rodadas', 'participantes', 'boloes', 'configuracoes'}


def assets_interface():
    from services.assets_vite import assets_da_entrada
    return assets_da_entrada('src/main.tsx')


def tipo_mensagem(categoria, texto):
    """Mesma classificação visual de templates/partials/alerts.html."""
    minusculo = texto.lower()
    if categoria in ('error', 'danger') or any(t in minusculo for t in ('erro', 'inválid', 'invalid', 'incorret', 'digite', 'somente para')):
        return 'error'
    if categoria == 'success' or 'sucesso' in minusculo or 'salvo' in minusculo:
        return 'success'
    return 'info'


@interface.get('/')
def index():
    authed = current_user.is_authenticated
    if authed and not pode_acessar_gestao(current_user):
        abort(403)
    # O React recebe apenas bolões em que há vínculo ativo de responsável.
    boloes = [b for b in g.boloes_disponiveis if any(
        p.usuario_id == current_user.id and p.status == 'ativo' and p.papel == 'responsavel'
        for p in b.participacoes)] if authed else []
    atual = bolao_atual()
    if atual not in boloes:
        atual = None
    # Um único bolão (mesmo com vários campeonatos): entra direto no campeonato principal.
    if atual is None and boloes and len({b.grupo_raiz_id for b in boloes}) == 1:
        atual = min(boloes, key=lambda b: (b.grupo_id is not None, b.id))
        lembrar_bolao(atual.id)
    dados = {
        'usuario': {'nome': current_user.nome, 'email': current_user.email} if authed else None,
        'boloes': [{
            'id': b.id, 'nome': b.nome, 'chave': b.chave,
            'campeonato': b.campeonato.nome, 'ano': b.campeonato.ano,
            'grupoId': b.grupo_raiz_id, 'status': b.status,
        } for b in boloes],
        'bolaoAtualId': atual.id if atual else None,
        'csrfToken': generate_csrf(),
        'mensagens': [{'tipo': tipo_mensagem(categoria, texto), 'texto': texto}
                      for categoria, texto in get_flashed_messages(with_categories=True)],
        'apiBase': url_for('interface.index') + 'api',
        'links': {
            'login': url_for('auth.login'),
            'logout': url_for('auth.logout'),
            'selecionar': url_for('interface.selecionar'),
        },
    }
    response = current_app.make_response(render_template(
        'interface.html', dados=dados, assets=assets_interface()))
    response.headers['Cache-Control'] = 'no-store'
    return response


@interface.post('/selecionar')
@login_required
def selecionar():
    if not pode_acessar_gestao(current_user):
        abort(403)
    if len(request.form.getlist('bolao_id')) != 1:
        abort(400)
    id = request.form.get('bolao_id', type=int)
    escolhido = next((b for b in g.boloes_disponiveis if b.id == id and any(
        p.usuario_id == current_user.id and p.status == 'ativo' and p.papel == 'responsavel'
        for p in b.participacoes)), None)
    if escolhido is None:
        abort(403)
    lembrar_bolao(escolhido.id)
    view = request.form.get('view', 'dashboard')
    if view not in VIEWS:
        view = 'dashboard'
    return redirect(url_for('interface.index') + '#' + view, code=303)
