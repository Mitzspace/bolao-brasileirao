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
def test_rotas_de_participante_nao_existem(gestao, path):
    app = gestao[0]
    app.config['WTF_CSRF_ENABLED'] = True
    client = app.test_client()
    assert client.post(path).status_code == 404  # sem gravar nada, antes mesmo do CSRF
    assert client.get(path).status_code in (302, 404)  # endereço antigo só leva à interface


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
    assert client.get('/interface/').status_code == 403
    assert client.get('/interface/api/dashboard').status_code == 403
    assert client.get('/logout').status_code == 302
    sessao(client, usuarios['responsavel'])
    assert client.get('/interface/api/dashboard').status_code == 200
    Participacao.query.filter_by(usuario_id=usuarios['responsavel']).one().status = 'removido'
    db.session.commit()
    assert client.get('/interface/api/dashboard').status_code == 403


def test_lancamento_sem_conta_e_preservacao(gestao):
    app, usuarios, bolao, pessoa, rodada, jogo = gestao
    client = app.test_client()
    sessao(client, usuarios['responsavel'])
    response = client.post('/interface/api/palpites', json={
        'participacaoId': pessoa, 'rodadaId': rodada, 'jogos': {str(jogo): {'casa': '2', 'fora': '1'}}})
    assert response.status_code == 200
    palpite = Palpite.query.one()
    assert palpite.participacao_id == pessoa
    assert palpite.origem == 'responsavel'
    assert palpite.lancado_por == usuarios['responsavel']
    assert PalpiteLog.query.count() == 1
    assert db.session.get(Participacao, pessoa).usuario_id is None
    # A tela antiga de palpite do próprio participante não existe mais.
    assert client.post(f'/rodada/{rodada}', data={f'casa_{jogo}': '9'}).status_code == 404
    assert Palpite.query.one().gols_casa == 2
