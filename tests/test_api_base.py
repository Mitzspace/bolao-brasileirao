"""Proteções da API da nova interface (routes/api.py)."""
from database import db
from models import Participacao
from tests.test_interface import entrar, gestao  # noqa: F401  (fixture reutilizada)


def test_api_sem_login_responde_json_401(client, gestao):
    resposta = client.get('/interface/api/contexto')
    assert resposta.status_code == 401
    assert resposta.is_json and 'erro' in resposta.get_json()


def test_contexto_sem_bolao_e_com_bolao(client, gestao):
    usuario, boloes = gestao
    entrar(client, usuario)
    dados = client.get('/interface/api/contexto').get_json()
    assert dados['usuario']['email'] == usuario.email
    assert dados['bolao'] is None  # dois bolões: nenhum escolhido ainda
    client.post('/interface/selecionar', data={'bolao_id': boloes[1].id})
    dados = client.get('/interface/api/contexto').get_json()
    assert dados['bolao']['id'] == boloes[1].id
    assert 'codigo_convite' not in dados['bolao']


def test_api_revogada_responde_403(client, gestao):
    from flask import g
    usuario, boloes = gestao
    entrar(client, usuario)
    for participacao in Participacao.query.filter_by(usuario_id=usuario.id).all():
        participacao.status = 'removido'
    db.session.commit()
    g.pop('_login_user', None)
    resposta = client.get('/interface/api/contexto')
    assert resposta.status_code == 403 and resposta.is_json


def test_erros_da_api_sao_json(client, gestao):
    usuario, _ = gestao
    entrar(client, usuario)
    resposta = client.get('/interface/api/nao-existe')
    assert resposta.status_code == 404 and resposta.is_json
    assert not client.get('/rota-que-nao-existe').is_json
    resposta = client.post('/interface/api/contexto')
    assert resposta.status_code == 405 and resposta.is_json


def test_mensagens_flash_trazem_tipo(client, app, gestao):
    from tests.test_interface import dados_renderizados
    usuario, _ = gestao
    client.post('/login', data={'email': usuario.email, 'senha': 'errada', 'nova_interface': '1'})
    with dados_renderizados(app) as dados:
        client.get('/interface/')
    assert dados[0]['mensagens'][0]['tipo'] == 'error'
    assert dados[0]['apiBase'] == '/interface/api'
