"""Aba Jogos: rodada atual, atrasados, navegação e horários da API (somente horários)."""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from database import db
from models import Jogo, Resultado, Rodada
from services import horarios
from tests.test_interface import entrar, gestao  # noqa: F401


@pytest.fixture(autouse=True)
def limpar_controle_de_frequencia():
    horarios._tentativas.clear()
    horarios._sucessos.clear()
    yield


def montar(bolao):
    camp = bolao.campeonato
    camp.codigo_api = 'BSA'
    r1, r2, r3 = (Rodada(nome=f'Rodada {n}', campeonato=camp) for n in (1, 2, 3))
    adiado = Jogo(time_casa='Remo', time_fora='Bahia', rodada=r1)
    feito = Jogo(time_casa='Santos', time_fora='Vasco', rodada=r1)
    feito2 = Jogo(time_casa='Grêmio', time_fora='Inter', rodada=r2)
    tarde = Jogo(time_casa='Flamengo', time_fora='Fluminense', rodada=r3, data=datetime(2030, 5, 3, 18, 30))
    cedo = Jogo(time_casa='Palmeiras', time_fora='Corinthians', rodada=r3, data=datetime(2030, 5, 2, 16, 0))
    db.session.add_all([adiado, feito, feito2, tarde, cedo])
    db.session.flush()
    db.session.add_all([Resultado(jogo=feito, gols_casa_real=1, gols_fora_real=0),
                        Resultado(jogo=feito2, gols_casa_real=0, gols_fora_real=0)])
    db.session.commit()
    return r1, r2, r3, adiado, tarde, cedo


def preparar(client, gestao):
    usuario, boloes = gestao
    dados = montar(boloes[0])
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': boloes[0].id})
    return dados


def test_agenda_rodada_atual_atrasados_e_inicio(client, gestao):
    r1, r2, r3, adiado, tarde, cedo = preparar(client, gestao)
    dados = client.get('/interface/api/jogos').get_json()
    assert dados['rodada']['id'] == r3.id and dados['rodada']['atual']
    assert [j['id'] for j in dados['jogos']] == [cedo.id, tarde.id]  # ordenados pelo horário
    assert dados['rodada']['inicioTexto'] == 'Qui 02/05 · 16:00'
    assert dados['rodada']['anteriorId'] == r2.id and dados['rodada']['proximaId'] is None
    assert [(a['id'], a['rodadaNome']) for a in dados['atrasados']] == [(adiado.id, 'Rodada 1')]


def test_navegacao_entre_rodadas_e_isolamento(client, gestao):
    r1, *_ = preparar(client, gestao)
    dados = client.get(f'/interface/api/jogos?rodada_id={r1.id}').get_json()
    assert dados['rodada']['id'] == r1.id and not dados['rodada']['atual']
    _, boloes = gestao
    outra = Rodada(nome='Rodada 9', campeonato=boloes[2].campeonato)
    db.session.add(outra)
    db.session.commit()
    assert client.get(f'/interface/api/jogos?rodada_id={outra.id}').status_code == 404


def test_atualizar_horarios_grava_somente_horario(client, gestao, app):
    r1, r2, r3, adiado, tarde, cedo = preparar(client, gestao)
    app.config['FOOTBALL_DATA_TOKEN'] = 'token-teste'
    nova_data = datetime(2030, 6, 1, 21, 0)
    api_falsa = [
        {'external_id': '10', 'matchday': 1, 'time_casa': 'Remo', 'time_fora': 'Bahia', 'data': nova_data,
         'finalizado': True, 'gols_casa_real': 3, 'gols_fora_real': 3},
    ]
    with patch('services.sync.buscar_jogos_football_data', return_value=api_falsa) as chamada:
        resposta = client.post('/interface/api/horarios/atualizar', json={}).get_json()
        assert resposta['status'] == 'ok' and resposta['horariosAtualizados'] == 1
        # Segunda chamada em seguida não consulta a API de novo.
        assert client.post('/interface/api/horarios/atualizar', json={}).get_json()['status'] == 'recente'
        assert chamada.call_count == 1
    db.session.refresh(adiado)
    assert adiado.data == nova_data
    assert adiado.resultado is None and not adiado.encerrado  # placar da API não é gravado


def test_atualizar_horarios_sem_token_ou_com_erro(client, gestao, app):
    preparar(client, gestao)
    app.config['FOOTBALL_DATA_TOKEN'] = ''
    with patch.dict('os.environ', {'FOOTBALL_DATA_TOKEN': ''}):
        assert client.post('/interface/api/horarios/atualizar', json={}).get_json()['status'] == 'sem_token'
    app.config['FOOTBALL_DATA_TOKEN'] = 'token-teste'
    from urllib.error import URLError
    with patch('services.sync.buscar_jogos_football_data', side_effect=URLError('fora do ar')):
        resposta = client.post('/interface/api/horarios/atualizar', json={'forcar': True})
    assert resposta.status_code == 200 and resposta.get_json()['status'] == 'erro'


def test_atualizar_horarios_exige_csrf(client, gestao, app):
    preparar(client, gestao)
    app.config['WTF_CSRF_ENABLED'] = True
    resposta = client.post('/interface/api/horarios/atualizar', json={})
    assert resposta.status_code == 403 and resposta.is_json


def test_sync_completo_continua_gravando_resultado(app, campeonato_teste):
    """A tela de sincronização atual não muda: com salvar_resultados padrão, grava o placar."""
    from services.sync import sync_informacoes_jogos
    r = Rodada(nome='Rodada 1', campeonato=campeonato_teste)
    jogo = Jogo(time_casa='Remo', time_fora='Bahia', rodada=r)
    db.session.add(jogo)
    db.session.commit()
    api_falsa = [{'external_id': '10', 'matchday': 1, 'time_casa': 'Remo', 'time_fora': 'Bahia',
                  'data': datetime.now() - timedelta(days=1), 'finalizado': True,
                  'gols_casa_real': 2, 'gols_fora_real': 1}]
    with patch('services.sync.buscar_jogos_football_data', return_value=api_falsa):
        sync_informacoes_jogos('t', campeonato_teste.id, 'BSA')
    assert jogo.resultado.gols_casa_real == 2 and jogo.encerrado
