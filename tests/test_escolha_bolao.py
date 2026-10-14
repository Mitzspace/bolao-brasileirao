import pytest
from flask import g
from database import db
from models import Participacao, Participante, Palpite
from tests.test_seletor_bolao import estrutura, login
from tests.test_ranking_privacidade import contextos
from utils import hash_senha


def autenticar(client, usuario):
    g.pop('_login_user', None)
    return client.post('/login', data={'email': usuario.email, 'senha': 'senha123'}, follow_redirects=True)


def test_login_sem_bolao(client, participante_teste):
    participante_teste.senha = hash_senha('senha123')
    db.session.commit()
    response = autenticar(client, participante_teste)
    assert response.status_code == 200
    assert response.request.path == '/boloes'
    assert 'Você ainda não participa de nenhum bolão' in response.text


def test_login_unico_e_tela_acessivel(client, participante_teste, campeonato_teste):
    b, _ = estrutura(participante_teste, campeonato_teste, 'Amigos')
    participante_teste.senha = hash_senha('senha123')
    db.session.commit()
    response = autenticar(client, participante_teste)
    assert response.request.path == '/' and response.request.args['bolao_id'] == str(b.id)
    with client.session_transaction() as sess:
        assert sess['bolao_id'] == b.id
        assert sess['bolao_usuario_id'] == participante_teste.id
    escolha = client.get('/boloes')
    assert escolha.status_code == 200 and 'Escolha seu bolão' in escolha.text
    assert 'Temporada 2025' in escolha.text and b.codigo_convite not in escolha.text


def test_varios_exigem_escolha_e_lembram_no_login(client, participante_teste, campeonato_teste):
    a, _ = estrutura(participante_teste, campeonato_teste, 'Amigos A')
    b, _ = estrutura(participante_teste, campeonato_teste, 'Amigos B')
    participante_teste.senha = hash_senha('senha123')
    db.session.commit()
    response = autenticar(client, participante_teste)
    assert response.request.path == '/boloes'
    assert a.nome in response.text and b.nome in response.text
    assert client.get('/ranking').location.endswith('/boloes')
    assert client.post('/boloes/selecionar', data={'bolao_id': b.id}).location.endswith(f'/?bolao_id={b.id}')
    client.get('/logout')
    response = autenticar(client, participante_teste)
    assert response.request.path == '/' and response.request.args['bolao_id'] == str(b.id)


@pytest.mark.parametrize('url', ['/', '/jogos', '/jogos/1', '/ranking', '/tabela', '/meus-palpites', '/rodada/1', '/rodada/1/palpites', '/admin/', '/admin/palpites'])
def test_rotas_sem_participacao_nao_expoem_dados(client, participante_teste, url):
    assert client.get(url).location.endswith('/login')
    login(client, participante_teste)
    assert client.get(url).location.endswith('/boloes')


@pytest.mark.parametrize('status', ['saiu', 'removido'])
def test_participacao_revogada_nao_autoriza_nem_grava(client, participante_teste, jogo_teste, status):
    b, part = estrutura(participante_teste, jogo_teste.rodada.campeonato, 'Restrito')
    login(client, participante_teste)
    client.get('/ranking')
    part.status = status
    db.session.commit()
    assert client.get('/ranking').location.endswith('/boloes')
    assert client.get(f'/ranking?bolao_id={b.id}').status_code == 403
    assert client.post('/boloes/selecionar', data={'bolao_id': b.id}).status_code == 403
    response = client.post(f'/rodada/{jogo_teste.rodada_id}', data={f'casa_{jogo_teste.id}': '2', f'fora_{jogo_teste.id}': '1'})
    assert response.location.endswith('/boloes')
    assert Palpite.query.count() == 0
    assert b.nome not in client.get('/boloes').text


def test_url_tem_precedencia_em_abas_diferentes(client, participante_teste, campeonato_teste):
    a, _ = estrutura(participante_teste, campeonato_teste, 'Mesmo nome')
    b, _ = estrutura(participante_teste, campeonato_teste, 'Mesmo nome')
    login(client, participante_teste)
    for bolao in (a, b, a):
        ctx = contextos(client.application, client, f'/ranking?bolao_id={bolao.id}')
        assert ctx['bolao_atual'].id == bolao.id


@pytest.mark.parametrize('parametro', ['999', 'abc', '', '1&bolao_id=2'])
def test_url_invalida_nao_cai_no_bolao_da_sessao(client, participante_teste, campeonato_teste, parametro):
    estrutura(participante_teste, campeonato_teste, 'Meu')
    login(client, participante_teste)
    client.get('/ranking')
    assert client.get(f'/ranking?bolao_id={parametro}').status_code == 403


def test_admin_global_precisa_participacao_e_nao_herda_escolha(client, participante_teste, campeonato_teste):
    a, _ = estrutura(participante_teste, campeonato_teste, 'Primeiro')
    b, _ = estrutura(participante_teste, campeonato_teste, 'Segundo')
    outro = Participante(nome='Global', email='global@example.com', admin_global=True, senha=hash_senha('senha123'))
    db.session.add(outro)
    db.session.commit()
    login(client, participante_teste)
    client.post('/boloes/selecionar', data={'bolao_id': b.id})
    client.get('/logout')
    response = autenticar(client, outro)
    assert 'Você ainda não participa' in response.text
    assert client.get(f'/ranking?bolao_id={b.id}').status_code == 403
    db.session.add_all([Participacao(bolao=a, usuario=outro, nome_exibicao='Global'),
                        Participacao(bolao=b, usuario=outro, nome_exibicao='Global')])
    db.session.commit()
    # Participar dos mesmos bolões não deve recuperar a escolha da outra conta.
    assert client.get('/ranking').location.endswith('/boloes')


def test_csrf_obrigatorio_na_selecao(app, client, participante_teste, campeonato_teste):
    b, _ = estrutura(participante_teste, campeonato_teste, 'Amigos')
    login(client, participante_teste)
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/boloes/selecionar', data={'bolao_id': b.id}).status_code == 403
