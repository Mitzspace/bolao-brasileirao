"""Configurações: perfil, e-mail de login, senha e responsáveis pela API."""
from werkzeug.security import check_password_hash

from database import db
from models import Participacao, Participante
from tests.test_interface import entrar, gestao  # noqa: F401


def preparar(client, gestao):
    usuario, boloes = gestao
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': boloes[0].id})
    return usuario, boloes


def test_nome_da_conta_nao_muda_nome_no_bolao(client, gestao):
    usuario, boloes = preparar(client, gestao)
    assert client.put('/interface/api/perfil', json={'nome': '  Novo   Nome '}).status_code == 200
    assert usuario.nome == 'Novo Nome'
    assert Participacao.query.filter_by(usuario_id=usuario.id, bolao_id=boloes[0].id).one().nome_exibicao == 'Responsável'
    assert client.put('/interface/api/perfil', json={'nome': 'A'}).status_code == 400


def test_trocar_email_exige_senha_e_email_livre(client, gestao):
    usuario, _ = preparar(client, gestao)
    assert client.put('/interface/api/perfil/email', json={'email': 'novo@example.com', 'senhaAtual': 'errada'}).status_code == 400
    r = client.put('/interface/api/perfil/email', json={'email': 'outro@example.com', 'senhaAtual': '123456'})
    assert r.status_code == 400 and 'Já existe' in r.get_json()['erro']
    assert client.put('/interface/api/perfil/email', json={'email': 'Novo@Example.com', 'senhaAtual': '123456'}).status_code == 200
    assert usuario.email == 'novo@example.com'
    client.get('/logout')
    assert client.post('/login', data={'email': 'novo@example.com', 'senha': '123456', 'nova_interface': '1'}).status_code == 302
    assert client.get('/interface/api/contexto').status_code == 200


def test_trocar_senha(client, gestao):
    usuario, _ = preparar(client, gestao)
    base = {'senhaAtual': '123456', 'novaSenha': 'nova-senha', 'confirmacao': 'nova-senha'}
    assert client.put('/interface/api/perfil/senha', json={**base, 'senhaAtual': 'x'}).status_code == 400
    assert client.put('/interface/api/perfil/senha', json={**base, 'confirmacao': 'outra'}).status_code == 400
    assert client.put('/interface/api/perfil/senha', json={**base, 'novaSenha': '123', 'confirmacao': '123'}).status_code == 400
    assert client.put('/interface/api/perfil/senha', json=base).status_code == 200
    assert check_password_hash(usuario.senha, 'nova-senha')


def test_adicionar_e_remover_responsavel(client, gestao):
    usuario, boloes = preparar(client, gestao)
    ana = Participacao(bolao=boloes[0], nome_exibicao='Ana')
    db.session.add(ana)
    db.session.commit()
    dados = client.get('/interface/api/responsaveis').get_json()
    assert [r['nome'] for r in dados['responsaveis']] == ['Responsável'] and dados['responsaveis'][0]['souEu']
    assert {p['nome'] for p in dados['participantesSemConta']} == {'Ana'}
    # Último responsável não pode sair.
    eu = dados['responsaveis'][0]['id']
    assert client.delete(f'/interface/api/responsaveis/{eu}').status_code == 409
    r = client.post('/interface/api/responsaveis', json={'email': 'ana@example.com', 'nome': 'Ana Conta',
                                                         'senha': 'segredo1', 'participacaoId': ana.id})
    assert r.status_code == 201
    assert ana.papel == 'responsavel' and ana.usuario.email == 'ana@example.com'
    assert client.post('/interface/api/responsaveis', json={'email': 'x'}).status_code == 400
    sair = client.delete(f'/interface/api/responsaveis/{eu}').get_json()
    assert sair['logout'] is True
    assert db.session.get(Participacao, eu).papel == 'participante'  # participação preservada


def test_responsaveis_de_outro_bolao_e_csrf(client, gestao, app):
    usuario, boloes = preparar(client, gestao)
    alheio = Participacao.query.filter_by(bolao_id=boloes[2].id, papel='responsavel').one()
    assert client.delete(f'/interface/api/responsaveis/{alheio.id}').status_code == 404
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.put('/interface/api/perfil', json={'nome': 'Hacker'}).status_code == 403
    assert db.session.get(Participante, usuario.id).nome == 'Responsável'
