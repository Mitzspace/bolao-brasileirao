from datetime import datetime, timedelta

import pytest
from flask import g
from werkzeug.security import generate_password_hash

from app import create_app
from database import db
from models import Bolao, Campeonato, Jogo, Palpite, PalpiteLog, Participacao, Participante, Rodada


@pytest.fixture
def gestao():
    app = create_app('testing', database_uri='sqlite:///:memory:')
    app.config['FEATURE_PARTICIPANTE_LOGIN'] = False
    with app.app_context():
        senha = generate_password_hash('senha123')
        usuarios = [Participante(nome=n, email=n + '@teste.com', senha=senha,
                                 admin_global=n == 'global', admin=n == 'legado')
                    for n in ['responsavel', 'comum', 'global', 'legado']]
        db.session.add_all(usuarios)
        db.session.flush()
        camp = Campeonato(nome='Campeonato', ano=2026)
        bolao = Bolao(nome='Bolão', campeonato=camp, criador=usuarios[0])
        db.session.add(bolao)
        db.session.flush()
        for usuario in usuarios[:2]:
            db.session.add(Participacao(bolao=bolao, usuario=usuario,
                nome_exibicao=usuario.nome,
                papel='responsavel' if usuario == usuarios[0] else 'participante'))
        pessoa = Participacao(bolao=bolao, nome_exibicao='Sem conta')
        rodada = Rodada(nome='Rodada 1', campeonato=camp)
        jogo = Jogo(time_casa='A', time_fora='B', rodada=rodada,
                    data=datetime.now() + timedelta(days=1))
        db.session.add_all([pessoa, rodada, jogo])
        db.session.commit()
        yield app, {u.nome: u.id for u in usuarios}, bolao.id, pessoa.id, rodada.id, jogo.id
        db.session.remove()
        db.drop_all()


def sessao(client, usuario):
    g.pop('_login_user', None)
    with client.session_transaction() as s:
        s['_user_id'] = str(usuario)
        s['_fresh'] = True


@pytest.mark.parametrize('path', ['/cadastro', '/meus-palpites', '/rodada/1'])
@pytest.mark.parametrize('method', ['get', 'post'])
def test_rotas_desativadas_antes_do_csrf(gestao, path, method):
    app = gestao[0]
    app.config['WTF_CSRF_ENABLED'] = True
    client = app.test_client()
    assert getattr(client, method)(path).status_code == 404


@pytest.mark.parametrize('nome,permitido', [('responsavel', True), ('global', True),
                                         ('comum', False), ('legado', False)])
def test_login_por_papel(gestao, nome, permitido):
    client = gestao[0].test_client()
    response = client.post('/login', data={'email': nome + '@teste.com', 'senha': 'senha123'})
    assert response.status_code == 302
    with client.session_transaction() as s:
        assert ('_user_id' in s) == permitido


def test_sessao_existente_e_revogacao(gestao):
    app, usuarios, *_ = gestao
    client = app.test_client()
    sessao(client, usuarios['comum'])
    assert client.get('/ranking').status_code == 403
    assert client.get('/boloes').status_code == 403
    assert client.get('/logout').status_code == 302
    sessao(client, usuarios['responsavel'])
    assert client.get('/ranking', follow_redirects=True).status_code == 200
    Participacao.query.filter_by(usuario_id=usuarios['responsavel']).one().status = 'removido'
    db.session.commit()
    assert client.get('/ranking').status_code == 403


def test_lancamento_sem_conta_menu_e_preservacao(gestao):
    app, usuarios, bolao, pessoa, rodada, jogo = gestao
    client = app.test_client()
    sessao(client, usuarios['responsavel'])
    for path in ['/', '/boloes', '/jogos', '/ranking', '/admin/palpites']:
        response = client.get(path, follow_redirects=True)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert '/meus-palpites' not in html
        assert '/cadastro' not in html
        assert 'Meus Palpites' not in html
    response = client.post(f'/b/{bolao}/palpites', data={
        'participante_id': pessoa, 'rodada_id': rodada,
        f'casa_{jogo}': '2', f'fora_{jogo}': '1'})
    assert response.status_code == 302
    palpite = Palpite.query.one()
    assert palpite.participacao_id == pessoa
    assert palpite.origem == 'responsavel'
    assert palpite.lancado_por == usuarios['responsavel']
    assert PalpiteLog.query.count() == 1
    assert db.session.get(Participacao, pessoa).usuario_id is None
    assert client.post(f'/rodada/{rodada}', data={f'casa_{jogo}': '9'}).status_code == 404
    assert Palpite.query.one().gols_casa == 2


def test_flag_reativa_fluxo_legado(gestao):
    app, usuarios, _, _, rodada, _ = gestao
    app.config['FEATURE_PARTICIPANTE_LOGIN'] = True
    client = app.test_client()
    assert client.get('/cadastro').status_code == 200
    client.post('/login', data={'email': 'comum@teste.com', 'senha': 'senha123'})
    assert client.get('/meus-palpites').status_code == 200
    assert client.get(f'/rodada/{rodada}').status_code == 200
    assert 'Meus Palpites' in client.get('/').get_data(as_text=True)
