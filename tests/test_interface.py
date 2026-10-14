"""Integração da interface com login, isolamento de bolões e proteção CSRF."""
from contextlib import contextmanager

import pytest
from flask import g, template_rendered

from database import db
from models import Bolao, Campeonato, Participacao, Participante
from tests.conftest import SENHA_TESTE


@pytest.fixture
def gestao(app):
    app.config['FEATURE_PARTICIPANTE_LOGIN'] = False
    usuario = Participante(nome='Responsável', email='gestor@example.com', senha=SENHA_TESTE)
    outro = Participante(nome='Outro', email='outro@example.com', senha=SENHA_TESTE)
    db.session.add_all([usuario, outro])
    db.session.flush()
    boloes = []
    for nome, dono in [('Amigos A', usuario), ('Amigos B', usuario), ('Privado', outro)]:
        campeonato = Campeonato(nome='Brasileirão ' + nome, ano=2026)
        bolao = Bolao(nome=nome, campeonato=campeonato, criador=dono)
        db.session.add(bolao)
        db.session.add(Participacao(bolao=bolao, usuario=dono,
            nome_exibicao=dono.nome, papel='responsavel', status='ativo'))
        boloes.append(bolao)
    db.session.commit()
    return usuario, boloes


def entrar(client, usuario):
    g.pop('_login_user', None)
    return client.post('/login', data={
        'email': usuario.email, 'senha': '123456', 'nova_interface': '1'})


@contextmanager
def dados_renderizados(app):
    dados = []
    def receber(sender, template, context, **extra):
        if template.name == 'interface.html':
            dados.append(context['dados'])
    template_rendered.connect(receber, app)
    try:
        yield dados
    finally:
        template_rendered.disconnect(receber, app)


def test_interface_publica_nao_expoe_dados(client, app, gestao):
    with dados_renderizados(app) as dados:
        response = client.get('/interface/')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'
    assert dados[0]['usuario'] is None and dados[0]['boloes'] == []


def test_login_real_e_erro_retornam_interface(client, gestao):
    usuario, _ = gestao
    erro = client.post('/login', data={
        'email': usuario.email, 'senha': 'errada', 'nova_interface': '1'})
    assert erro.location.endswith('/interface/')
    with client.session_transaction() as sess:
        assert '_user_id' not in sess
    assert entrar(client, usuario).location.endswith('/interface/')


def test_selecao_isola_boloes_e_links(client, app, gestao):
    usuario, boloes = gestao
    entrar(client, usuario)
    with dados_renderizados(app) as dados:
        client.get('/interface/')
    assert {b['id'] for b in dados[0]['boloes']} == {b.id for b in boloes[:2]}
    assert dados[0]['bolaoAtualId'] is None
    assert all('codigo_convite' not in b for b in dados[0]['boloes'])
    response = client.post('/interface/selecionar', data={'bolao_id': boloes[1].id, 'view': 'rodadas'})
    assert response.status_code == 303 and response.location.endswith('/interface/#rodadas')
    with dados_renderizados(app) as dados:
        client.get('/interface/')
    assert dados[0]['bolaoAtualId'] == boloes[1].id
    assert dados[0]['links']['palpites'].startswith(f'/b/{boloes[1].id}/')
    assert client.post('/interface/selecionar', data={'bolao_id': boloes[2].id}).status_code == 403
    assert client.post('/interface/selecionar', data={'bolao_id': 'invalido'}).status_code == 403


def test_revogacao_e_participante_sem_login(client, gestao):
    usuario, boloes = gestao
    entrar(client, usuario)
    for participacao in Participacao.query.filter_by(usuario_id=usuario.id).all():
        participacao.status = 'removido'
    db.session.commit()
    g.pop('_login_user', None)
    assert client.get('/interface/').status_code == 403
    assert client.post('/interface/selecionar', data={'bolao_id': boloes[0].id}).status_code == 403


def test_selecao_csrf_logout_e_destino_fixo(client, app, gestao):
    usuario, boloes = gestao
    entrar(client, usuario)
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/interface/selecionar', data={'bolao_id': boloes[0].id}).status_code == 403
    with dados_renderizados(app) as dados:
        client.get('/interface/')
    response = client.post('/interface/selecionar', data={
        'bolao_id': boloes[0].id, 'csrf_token': dados[0]['csrfToken'], 'view': 'https://evil.example'})
    assert response.location.endswith('/interface/#dashboard')
    assert client.get('/logout?nova_interface=1').location.endswith('/interface/')
    with client.session_transaction() as sess:
        assert '_user_id' not in sess and 'bolao_id' not in sess
