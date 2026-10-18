"""A criação via API grava a fonte do campeonato (informada, do modelo ou inferida)."""
import pytest

from models import Bolao
from tests.test_interface import entrar, gestao  # noqa: F401


@pytest.fixture
def autenticado(client, gestao):
    entrar(client, gestao[0])
    return client


def _criar(client, **campos):
    resposta = client.post('/interface/api/boloes', json={'nome': 'Copa da firma', 'ano': 2026, **campos})
    assert resposta.status_code == 201, resposta.get_json()
    return Bolao.query.get(resposta.get_json()['bolaoId']).campeonato


@pytest.mark.parametrize('campos,fonte', [
    ({'modelo': 'libertadores'}, 'api-football'),
    ({'modelo': 'brasileirao'}, 'football-data'),
    ({'campeonato': 'Liga X', 'codigoApi': '999', 'fonte_api': 'api-football'}, 'api-football'),
    ({'campeonato': 'Liga Y', 'codigoApi': 'PL'}, 'football-data'),
])
def test_fonte_gravada(autenticado, campos, fonte):
    assert _criar(autenticado, **campos).fonte_api == fonte


def test_fonte_invalida_rejeitada(autenticado):
    resposta = autenticado.post('/interface/api/boloes', json={
        'nome': 'Copa', 'ano': 2026, 'campeonato': 'X', 'codigoApi': 'PL', 'fonte_api': 'outra'})
    assert resposta.status_code == 400
