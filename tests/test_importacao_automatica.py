"""Importação dos jogos ao criar o bolão e criação de jogos novos pelo worker (ESPN)."""
from unittest.mock import patch

import pytest

from database import db
from models import Bolao, Campeonato, Jogo, Rodada
from services.sync import sync_competicao, sync_jogos
from services.sync_automatico import sincronizar_ciclo
from tests.test_criacao_copas_api import autenticado, criar  # noqa: F401
from tests.test_interface import gestao  # noqa: F401


def item(eid, fase='LAST_16', casa='Flamengo', fora='Palmeiras'):
    rotulos = {'LAST_16': 'Oitavas de final', 'QUARTER_FINALS': 'Quartas de final'}
    return dict(external_id=str(eid), estagio=fase, fase=rotulos[fase], matchday=None,
                time_casa=casa, time_fora=fora, data=None, finalizado=False,
                gols_casa_real=None, gols_fora_real=None)


def campeonato():
    camp = Campeonato(nome='Libertadores', codigo_api='conmebol.libertadores', fonte_api='espn', ano=2026)
    db.session.add(camp)
    db.session.commit()
    return camp


@pytest.fixture
def importar_ao_criar(app, monkeypatch):
    # chave_api também lê o ambiente (o .env local pode ter token).
    monkeypatch.delenv('FOOTBALL_DATA_TOKEN', raising=False)
    monkeypatch.delenv('API_FOOTBALL_KEY', raising=False)
    app.config.update(IMPORTAR_JOGOS_AO_CRIAR=True, FOOTBALL_DATA_TOKEN=None, API_FOOTBALL_KEY=None)


# ---------- Worker ----------

def test_worker_espn_cria_jogos_de_fase_nova_sem_duplicar(app):
    camp = campeonato()
    sync_jogos(None, camp.id, camp.codigo_api, jogos_api=[item(1)], campeonato_completo=True)
    sorteio = [item(1), item(2, 'QUARTER_FINALS', 'Grêmio', 'Santos')]
    with patch('services.importador_espn.buscar_jogos_espn', return_value=sorteio):
        res = sync_competicao(None, 'conmebol.libertadores', 2026, fonte_api='espn')
        sync_competicao(None, 'conmebol.libertadores', 2026, fonte_api='espn')
    assert res[camp.id]['criados'] == 1
    assert Jogo.query.count() == 2
    assert {r.nome for r in Rodada.query} == {'Rodada 10 · Oitavas de final', 'Rodada 11 · Quartas de final'}


def test_worker_espn_nao_cria_rodada_vazia_para_jogo_ja_salvo(app):
    camp = campeonato()
    antiga = Rodada(nome='Rodada 4 · Fase de grupos', campeonato=camp)
    db.session.add(antiga)
    db.session.flush()
    db.session.add(Jogo(time_casa='Flamengo', time_fora='Palmeiras', rodada_id=antiga.id,
                        external_fonte='espn', external_id='1'))
    db.session.commit()
    grupo = {**item(1), 'estagio': 'GROUP_STAGE', 'fase': 'Fase de grupos', 'matchday': 1}
    with patch('services.importador_espn.buscar_jogos_espn', return_value=[grupo]):
        sync_competicao(None, 'conmebol.libertadores', 2026, fonte_api='espn')
    assert [r.nome for r in Rodada.query] == ['Rodada 4 · Fase de grupos']


def test_worker_espn_preenche_campeonato_vazio(app):
    app.config.update(FOOTBALL_DATA_TOKEN=None, API_FOOTBALL_KEY=None)
    camp = campeonato()
    with patch('services.importador_espn.buscar_jogos_espn', return_value=[item(1)]):
        sincronizar_ciclo(app)
    assert Jogo.query.join(Rodada).filter(Rodada.campeonato_id == camp.id).count() == 1


def test_worker_football_data_continua_sem_criar_jogos(app):
    camp = Campeonato(nome='Brasileirão', codigo_api='BSA', fonte_api='football-data', ano=2026)
    db.session.add(camp)
    db.session.add(Rodada(nome='Rodada 1', campeonato=camp))
    db.session.commit()
    novo = {**item(9), 'estagio': 'REGULAR_SEASON', 'matchday': 1}
    with patch('services.sync.buscar_jogos', return_value=[novo]):
        sync_competicao('token', 'BSA', 2026)
    assert Jogo.query.count() == 0


# ---------- Criação do bolão ----------

def test_criacao_espn_importa_jogos(autenticado, importar_ao_criar):
    with patch('services.importador_espn.buscar_jogos_espn', return_value=[item(1), item(2)]) as busca:
        r = criar(autenticado, modelo='libertadores')
    assert r.status_code == 201, r.get_json()
    busca.assert_called_with('conmebol.libertadores', '2026', data_inicio=None, data_fim=None)  # verificação + importação
    assert r.get_json()['importacao'] == {'sucesso': True, 'mensagem': '2 jogos importados em 1 rodadas.'}
    camp = db.session.get(Bolao, r.get_json()['bolaoId']).campeonato
    assert Jogo.query.join(Rodada).filter(Rodada.campeonato_id == camp.id).count() == 2


def test_falha_na_importacao_nao_desfaz_bolao(autenticado, importar_ao_criar):
    from services.importador_espn import ErroEspn
    with patch('services.importador_espn.buscar_jogos_espn', side_effect=ErroEspn('ESPN fora do ar')):
        r = criar(autenticado, modelo='copadobrasil')
    assert r.status_code == 201
    importacao = r.get_json()['importacao']
    assert not importacao['sucesso'] and 'ESPN fora do ar' in importacao['mensagem']
    assert db.session.get(Bolao, r.get_json()['bolaoId']) is not None


def test_temporada_sem_jogos_impede_criacao(autenticado, importar_ao_criar):
    antes = Bolao.query.count()
    with patch('services.importador_espn.buscar_jogos_espn', return_value=[]):
        r = criar(autenticado, modelo='mineiro')
    assert r.status_code == 400
    assert 'não existe' in r.get_json()['erro']
    assert Bolao.query.count() == antes


def test_provedor_pago_sem_chave_nao_consulta(autenticado, importar_ao_criar):
    with patch('services.sync.buscar_jogos') as busca:
        r = criar(autenticado, modelo='brasileirao')
    busca.assert_not_called()
    assert 'FOOTBALL' not in r.get_json()['importacao']['mensagem']
    assert 'chave da football-data.org' in r.get_json()['importacao']['mensagem']


def test_importacao_desligada_por_configuracao(autenticado, app):
    app.config.update(IMPORTAR_JOGOS_AO_CRIAR=False)
    with patch('services.sync.buscar_jogos') as busca:
        r = criar(autenticado, modelo='libertadores')
    busca.assert_not_called()
    assert 'importacao' not in r.get_json()


def test_verificar_temporada_antes_de_criar(autenticado, importar_ao_criar):
    corpo = {'campeonato': 'Mineiro', 'ano': 2031, 'codigoApi': 'bra.camp.mineiro', 'fonte_api': 'espn'}
    with patch('services.importador_espn.buscar_jogos_espn', return_value=[]):
        r = autenticado.post('/interface/api/boloes/verificar-temporada', json=corpo)
    assert r.status_code == 400 and 'não existe' in r.get_json()['erro']
    with patch('services.importador_espn.buscar_jogos_espn', return_value=[item(1)]):
        r = autenticado.post('/interface/api/boloes/verificar-temporada', json=corpo)
    assert r.status_code == 200
