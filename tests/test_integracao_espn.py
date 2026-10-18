"""Fluxo ESPN sem token, isolamento por rodada e configuração dos provedores."""
from unittest.mock import patch

from database import db
from models import Campeonato, Jogo, Rodada
from services.competicoes import nomeador_rodadas
from services.sync import sync_jogos, sync_resultados
from services.sync_automatico import sincronizar_ciclo
from tests.test_api_campeonatos import preparar
from tests.test_interface import gestao  # noqa: F401


def item(eid, fase='LAST_16'):
    return dict(external_id=str(eid), estagio=fase, fase='Oitavas de final' if fase == 'LAST_16' else 'Final',
                matchday=None, time_casa='Flamengo', time_fora='Palmeiras', data=None,
                finalizado=False, gols_casa_real=None, gols_fora_real=None)


def campeonato():
    camp = Campeonato(nome='Libertadores', codigo_api='conmebol.libertadores', fonte_api='espn', ano=2026)
    db.session.add(camp)
    db.session.commit()
    return camp


def test_importa_so_rodada_local_sem_duplicar(app):
    camp = campeonato()
    jogos = [item(1), item(2, 'FINAL')]
    with patch('services.importador_espn.buscar_jogos_espn', return_value=jogos):
        assert sync_jogos(None, camp.id, camp.codigo_api, rodada_api='10')['criados'] == 1
        assert sync_jogos(None, camp.id, camp.codigo_api, rodada_api='10')['criados'] == 0
    assert Jogo.query.one().external_id == '1'
    assert Rodada.query.one().nome == 'Rodada 10 · Oitavas de final'


def test_resultados_respeitam_rodada_local(app):
    camp = campeonato()
    sync_jogos(None, camp.id, camp.codigo_api, jogos_api=[item(1), item(2, 'FINAL')], campeonato_completo=True)
    placares = [dict(external_id=str(i), gols_casa_real=2, gols_fora_real=1) for i in (1, 2)]
    with patch('services.importador_espn.buscar_resultados_espn', return_value=placares):
        res = sync_resultados(None, camp.codigo_api, fonte_api='espn', rodada_api='10')
    assert res['atualizados'] == 1
    assert Jogo.query.filter_by(external_id='2').one().resultado is None


def test_grupos_sem_rodada_oficial_preservam_fase():
    grupo = dict(estagio='GROUP_STAGE', matchday=None)
    nome = nomeador_rodadas('espn', [grupo], 'conmebol.libertadores')
    assert nome(grupo) == 'Rodada 4 · Fase de grupos'


def test_worker_espn_funciona_sem_chaves_e_compartilha_consulta(app):
    app.config.update(FOOTBALL_DATA_TOKEN=None, API_FOOTBALL_KEY=None)
    for _ in range(2):
        camp = campeonato()
        db.session.add(Rodada(nome='Rodada 1', campeonato=camp))
    db.session.commit()
    with patch('services.sync_automatico.sync_competicao', return_value={}) as sync:
        sincronizar_ciclo(app)
    sync.assert_called_once_with(None, 'conmebol.libertadores', 2026, fonte_api='espn')


def test_sync_manual_sem_token_com_codigo_longo(client, gestao, app):
    bolao, *_ = preparar(client, gestao)
    gestao[0].admin_global = True
    bolao.campeonato.fonte_api = 'espn'
    bolao.campeonato.codigo_api = 'conmebol.sudamericana'
    db.session.commit()
    app.config.update(FOOTBALL_DATA_TOKEN=None, API_FOOTBALL_KEY=None)
    with patch('services.importador_espn.buscar_jogos_espn', return_value=[]):
        r = client.post('/interface/api/campeonato/sincronizar', json={
            'acao': 'jogos', 'campeonatoCompleto': True, 'competicao': 'conmebol.sudamericana'})
    assert r.status_code == 200, r.get_json()
    agenda = client.get('/interface/api/jogos').get_json()
    assert agenda['horarios']['fonte'] == 'ESPN'
    assert agenda['horarios']['configurado'] is True


def test_tabela_espn_nao_consulta_provedor_errado(client, gestao):
    bolao, *_ = preparar(client, gestao)
    bolao.campeonato.fonte_api = 'espn'
    db.session.commit()
    with patch('services.classificacao._requisitar_api') as football_data,             patch('services.classificacao_espn.requisitar_standings', return_value={'name': 'Copa'}) as espn:
        tabela = client.get('/interface/api/tabela').get_json()
    football_data.assert_not_called()
    espn.assert_called_once()
    assert not tabela['sucesso'] and 'aba Jogos' in tabela['erro']


def test_erro_espn_em_horarios_nao_vira_erro_500(client, gestao):
    from services.importador_espn import ErroEspn
    bolao, *_ = preparar(client, gestao)
    bolao.campeonato.fonte_api = 'espn'
    db.session.commit()
    with patch('services.horarios.sync_informacoes_jogos', side_effect=ErroEspn('Temporada indisponível')):
        r = client.post('/interface/api/horarios/atualizar', json={'forcar': True})
    assert r.status_code == 200 and r.get_json()['status'] == 'erro'
