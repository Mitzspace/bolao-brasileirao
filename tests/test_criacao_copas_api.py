"""Modelos de competição e eliminação na criação via API."""
import pytest

from database import db
from models import Bolao
from services.competicoes import MODELOS_COMPETICAO
from services.criacao_bolao import AVISO_API_FOOTBALL
from tests.test_interface import entrar, gestao  # noqa: F401


@pytest.fixture
def autenticado(client, gestao):
    entrar(client, gestao[0])
    return client


def criar(client, **campos):
    return client.post('/interface/api/boloes', json={'nome': 'Copa da firma', 'ano': 2026, **campos})


def test_lista_modelos(autenticado):
    resposta = autenticado.get('/interface/api/boloes/fontes')
    assert resposta.status_code == 200
    modelos = {m['chave']: m for m in resposta.get_json()['modelos']}
    assert modelos.keys() == MODELOS_COMPETICAO.keys()
    for chave, esperado in MODELOS_COMPETICAO.items():
        assert {campo: modelos[chave][campo] for campo in esperado} == esperado
    assert modelos['brasileirao']['aviso'] is None
    assert modelos['brasileirao']['fonte_api'] == 'football-data'
    for chave in ('libertadores', 'sulamericana', 'copadobrasil', 'mineiro'):
        assert modelos[chave]['fonte_api'] == 'espn'
        assert modelos[chave]['aviso'] is None


@pytest.mark.parametrize('modelo,nome,codigo,fonte', [
    ('libertadores', 'Copa Libertadores', 'conmebol.libertadores', 'espn'),
    ('sulamericana', 'Copa Sul-Americana', 'conmebol.sudamericana', 'espn'),
    ('copadobrasil', 'Copa do Brasil', 'bra.copa_do_brazil', 'espn'),
    ('mineiro', 'Campeonato Mineiro', 'bra.camp.mineiro', 'espn'),
    ('brasileirao', 'Brasileirão Série A', 'BSA', 'football-data'),
])
@pytest.mark.parametrize('vazio', [None, '', '   '])
def test_modelo_preenche_campos(autenticado, modelo, nome, codigo, fonte, vazio):
    resposta = criar(autenticado, modelo=modelo, campeonato=vazio, codigoApi=vazio,
                     eliminacao_participantes=True)
    assert resposta.status_code == 201
    novo = db.session.get(Bolao, resposta.get_json()['bolaoId'])
    assert (novo.campeonato.nome, novo.campeonato.codigo_api, novo.campeonato.fonte_api) == (nome, codigo, fonte)
    assert novo.eliminacao_participantes is True


@pytest.mark.parametrize('campos', [
    {'campeonato': 'Copa personalizada', 'codigoApi': 'cl'},
    {'campeonato_nome': 'Copa personalizada', 'codigo_api': 'cl'},
])
def test_campos_informados_prevalecem(autenticado, campos):
    resposta = criar(autenticado, modelo='libertadores', **campos)
    assert resposta.status_code == 201
    novo = db.session.get(Bolao, resposta.get_json()['bolaoId'])
    assert (novo.campeonato.nome, novo.campeonato.codigo_api) == ('Copa personalizada', 'CL')
    assert novo.eliminacao_participantes is False
    assert 'aviso' not in resposta.get_json()


@pytest.mark.parametrize('campos', [{'modelo': 'libertadores'}, {'campeonato': 'Outro campeonato'}])
def test_eliminacao_desligada_por_padrao(autenticado, campos):
    resposta = criar(autenticado, **campos)
    assert resposta.status_code == 201
    assert db.session.get(Bolao, resposta.get_json()['bolaoId']).eliminacao_participantes is False


def test_eliminacao_explicitamente_desligada(autenticado):
    resposta = criar(autenticado, modelo='libertadores', eliminacao_participantes=False)
    assert resposta.status_code == 201
    assert db.session.get(Bolao, resposta.get_json()['bolaoId']).eliminacao_participantes is False


@pytest.mark.parametrize('modelo', ['invalido', '', [], {}, 1, True])
def test_modelo_invalido(autenticado, modelo):
    antes = Bolao.query.count()
    assert criar(autenticado, modelo=modelo, campeonato='Copa').status_code == 400
    assert Bolao.query.count() == antes


@pytest.mark.parametrize('valor', ['false', 0, 1, None, []])
def test_eliminacao_exige_booleano(autenticado, valor):
    assert criar(autenticado, modelo='libertadores', eliminacao_participantes=valor).status_code == 400


@pytest.mark.parametrize('campos', [
    {'campeonato': 'Outra copa', 'codigoApi': '71'},
    {'campeonato': 'Outra copa', 'codigoApi': '13', 'fonte_api': 'api-football'},
])
def test_aviso_plano_pago_api_football(autenticado, campos):
    resposta = criar(autenticado, **campos)
    assert resposta.status_code == 201
    assert resposta.get_json()['aviso'] == AVISO_API_FOOTBALL


def test_modelos_espn_sem_aviso(autenticado):
    resposta = criar(autenticado, modelo='libertadores')
    assert resposta.status_code == 201
    assert 'aviso' not in resposta.get_json()


def test_aviso_plano_pago_football_data(autenticado):
    resposta = criar(autenticado, campeonato='Outra copa', codigoApi='cli')
    assert resposta.status_code == 201
    assert resposta.get_json()['aviso'] == (
        'A sincronização de Libertadores/Sul-Americana na football-data.org exige token de plano pago.')
    assert db.session.get(Bolao, resposta.get_json()['bolaoId']).campeonato.fonte_api == 'football-data'


def test_criar_bolao_com_fonte_explicita(gestao):
    from services.criacao_bolao import criar_bolao
    novo = criar_bolao(gestao[0], 'Copa X', 'Copa X', 2024, 'ABC', [], set(), fonte_api='api-football')
    assert novo.campeonato.fonte_api == 'api-football'
    espn = criar_bolao(gestao[0], 'Copa E', 'Copa E', 2024, 'conmebol.libertadores', [], set(),
                       fonte_api='espn')
    assert espn.campeonato.fonte_api == 'espn'
    with pytest.raises(ValueError):
        criar_bolao(gestao[0], 'Copa Y', 'Copa Y', 2024, 'ABC', [], set(), fonte_api='outra')
