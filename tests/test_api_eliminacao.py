import pytest

from database import db
from models import Campeonato, CorteEliminacao, Rodada
from tests.apoio import estrutura, login
from tests.test_eliminacao import disputa


@pytest.fixture
def gestao(client, disputa, participante_teste):
    login(client, participante_teste)
    b = disputa[0]
    client.post('/interface/selecionar', data={'bolao_id': b.id})
    return client, disputa


def test_configuracao_toggle_preserva_cortes(gestao):
    client, (b, _, rs, _, c) = gestao
    resposta = client.get('/interface/api/eliminacao')
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados['eliminacaoParticipantes'] is True
    assert [r['id'] for r in dados['rodadas']] == [r.id for r in rs]
    assert dados['cortes'][0]['id'] == c.id
    for metodo, ligado in [('put', False), ('post', True)]:
        assert getattr(client, metodo)('/interface/api/eliminacao', json={'eliminacaoParticipantes': ligado}).status_code == 200
        assert db.session.get(type(b), b.id).eliminacao_participantes == ligado
        assert CorteEliminacao.query.count() == 1


@pytest.mark.parametrize('valor', [None, 0, 'true', [], {}])
def test_toggle_invalido(gestao, valor):
    client, _ = gestao
    assert client.put('/interface/api/eliminacao', json={'eliminacaoParticipantes': valor}).status_code == 400


@pytest.mark.parametrize('valor', [0, -1, True, 1.5, '2', None, 2147483648])
def test_classificados_invalidos(gestao, valor):
    client, (_, _, rs, _, _) = gestao
    assert client.post('/interface/api/eliminacao/cortes', json={'rodadaId': rs[0].id, 'classificados': valor}).status_code == 400


def test_criar_ordenar_validar_e_remover(gestao):
    client, (b, _, rs, _, _) = gestao
    def criar(r, n):
        return client.post('/interface/api/eliminacao/cortes', json={'rodadaId': r.id, 'classificados': n})
    assert criar(rs[1], 2).status_code == 400
    assert criar(rs[0], 2).status_code == 400
    assert criar(rs[2], 3).status_code == 400
    assert criar(rs[2], 2).status_code == 400
    assert criar(rs[2], 1).status_code == 201
    assert criar(rs[0], 3).status_code == 201
    cortes = client.get('/interface/api/eliminacao').get_json()['cortes']
    assert [c['classificados'] for c in cortes] == [3, 2, 1]
    assert client.delete(f"/interface/api/eliminacao/cortes/{cortes[1]['id']}").status_code == 200
    assert CorteEliminacao.query.filter_by(bolao_id=b.id).count() == 2


def test_isolamento_campeonato_bolao(gestao, participante_teste):
    client, (b, _, rs, _, _) = gestao
    outro = Campeonato(nome='Outro', ano=2026)
    rodada = Rodada(nome='Rodada 1', campeonato=outro)
    db.session.add_all([outro, rodada])
    db.session.commit()
    outro_b, _ = estrutura(participante_teste, outro, 'Outro bolão')
    corte = CorteEliminacao(bolao=outro_b, rodada=rodada, classificados=1)
    db.session.add(corte)
    db.session.commit()
    assert client.post('/interface/api/eliminacao/cortes', json={'rodadaId': rodada.id, 'classificados': 1}).status_code == 400
    assert client.delete(f'/interface/api/eliminacao/cortes/{corte.id}').status_code == 404
    assert db.session.get(CorteEliminacao, corte.id) is not None


def test_contagem_json_geral_e_rodada(gestao):
    client, (b, ps, rs, _, _) = gestao
    url = f'/interface/api/boloes/{b.id}/classificacao'
    dados = client.get(url).get_json()
    assert dados['eliminadosOcultos'] == 1
    assert [p['participacaoId'] for p in dados['ranking']] == [p.id for p in ps[:2]]
    assert client.get(f'{url}?rodada_id={rs[1].id}').get_json()['eliminadosOcultos'] == 0
    assert client.get(f'{url}?rodada_id={rs[2].id}').get_json()['eliminadosOcultos'] == 1


def test_sem_login(client):
    assert client.get('/interface/api/eliminacao').status_code == 401
    assert client.post('/interface/api/eliminacao/cortes', json={}).status_code == 401


def test_sem_permissao(gestao):
    client, (_, ps, _, _, c) = gestao
    ps[0].papel = 'participante'
    db.session.commit()
    assert client.get('/interface/api/eliminacao').status_code == 403
    assert client.delete(f'/interface/api/eliminacao/cortes/{c.id}').status_code == 403


def test_csrf_obrigatorio(gestao, app):
    client, (_, _, rs, _, c) = gestao
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.put('/interface/api/eliminacao', json={'eliminacaoParticipantes': False}).status_code == 403
    assert client.post('/interface/api/eliminacao/cortes', json={'rodadaId': rs[0].id, 'classificados': 3}).status_code == 403
    assert client.delete(f'/interface/api/eliminacao/cortes/{c.id}').status_code == 403
