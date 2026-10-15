"""Regressões dos defeitos reproduzidos na revisão de 12/10/2026."""
from datetime import datetime

import pytest
from flask import g
from sqlalchemy import event

from database import db
from models import Bolao, Campeonato, Jogo, Palpite, Participacao, Resultado, Rodada
from tests.test_fundacao_multibolao import autorizar_responsavel


@pytest.fixture
def gestao(client, admin_teste, jogo_teste):
    admin_teste.admin_global = True
    autorizar_responsavel(admin_teste, jogo_teste)
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_teste.id)
    g.pop('_login_user', None)
    return client, jogo_teste


@pytest.mark.parametrize('valor', ['abc', '-1', '1.5', '', '999999999999999999999'])
def test_resultado_invalido_nao_grava(gestao, valor):
    client, jogo = gestao
    response = client.post(f'/interface/api/jogos/{jogo.id}/resultado', json={'golsCasa': valor, 'golsFora': '0'})
    assert response.status_code == 400
    assert Resultado.query.count() == 0


@pytest.mark.parametrize('editar', [False, True])
@pytest.mark.parametrize('campo,valor', [('data', 'invalida'), ('casa', ''), ('rodadaId', '')])
def test_jogo_invalido_preserva_dados(gestao, editar, campo, valor):
    client, jogo = gestao
    dados = dict(casa='Novo time', fora='Outro', rodadaId=jogo.rodada_id, data='2026-12-10T12:00')
    dados[campo] = valor
    response = (client.put(f'/interface/api/jogos/{jogo.id}', json=dados) if editar
                else client.post('/interface/api/jogos', json=dados))
    assert response.status_code in (400, 404)
    db.session.refresh(jogo)
    assert jogo.time_casa == 'Time A'
    assert Jogo.query.count() == 1


def test_rodada_invalida(gestao):
    client, jogo = gestao
    assert client.post('/interface/api/rodadas', json={'nome': ''}).status_code == 400
    assert Rodada.query.count() == 1


def test_resultado_valido_inclui_zero(gestao):
    client, jogo = gestao
    assert client.post(f'/interface/api/jogos/{jogo.id}/resultado', json={'golsCasa': 0, 'golsFora': 1}).status_code == 200
    assert Resultado.query.one().gols_casa_real == 0


def test_sincronizacao_de_jogos_atualiza_existente_e_cria_novo(gestao, monkeypatch):
    client, jogo = gestao
    jogo.external_fonte, jogo.external_id = 'football-data.org', '10'
    db.session.commit()
    g.pop('_login_user', None)
    data = datetime(2026, 12, 10, 12)
    itens = [dict(external_id=id, time_casa='A', time_fora='B', data=data, matchday=1, finalizado=False,
                  gols_casa_real=None, gols_fora_real=None) for id in ['10', '11']]
    monkeypatch.setattr('services.sync.buscar_jogos_football_data', lambda **kwargs: itens)
    dados = dict(acao='jogos', token='teste', nomeRodada=jogo.rodada.nome, competicao='BSA')
    for _ in range(2):
        response = client.post('/interface/api/campeonato/sincronizar', json=dados)
        assert response.status_code == 200, response.get_json()
    assert Jogo.query.count() == 2
    db.session.refresh(jogo)
    assert jogo.data == data


def test_mesmo_jogo_da_api_em_dois_boloes_nao_se_mistura(gestao, monkeypatch):
    """Cada bolão tem o seu campeonato: o 2º bolão cria os próprios jogos, sem mexer nos do 1º."""
    client, jogo = gestao
    jogo.external_fonte, jogo.external_id = 'football-data.org', '10'
    outro_camp = Campeonato(nome='Brasileirão', ano=2026, codigo_api='BSA')
    outro = Bolao(nome='Outro bolão', campeonato=outro_camp, criador=Bolao.query.first().criador)
    db.session.add(Participacao(bolao=outro, usuario=Bolao.query.first().criador, nome_exibicao='Admin', papel='responsavel'))
    db.session.commit()
    itens = [dict(external_id='10', time_casa='A', time_fora='B', data=datetime(2026, 12, 10, 12), matchday=1,
                  finalizado=False, gols_casa_real=None, gols_fora_real=None)]
    monkeypatch.setattr('services.sync.buscar_jogos_football_data', lambda **kwargs: itens)
    g.pop('_login_user', None)
    sel = client.post('/interface/selecionar', data={'bolao_id': outro.id})
    assert sel.status_code == 303, sel.status_code
    g.pop('_login_user', None)
    r = client.post('/interface/api/campeonato/sincronizar', json={'acao': 'jogos', 'token': 't', 'rodadaApi': '1'})
    assert r.status_code == 200
    assert Jogo.query.count() == 2 and jogo.rodada.campeonato_id != outro_camp.id
    assert Jogo.query.join(Rodada).filter(Rodada.campeonato_id == outro_camp.id).count() == 1


def test_sincronizacao_de_resultados(gestao, monkeypatch):
    client, jogo = gestao
    jogo.external_fonte, jogo.external_id = 'football-data.org', '10'
    db.session.commit()
    g.pop('_login_user', None)
    monkeypatch.setattr('services.sync.buscar_resultados_football_data', lambda **kwargs: [
        dict(external_id='10', gols_casa_real=2, gols_fora_real=1, data=None)])
    response = client.post('/interface/api/campeonato/sincronizar', json={'acao': 'resultados', 'token': 'teste', 'competicao': 'BSA'})
    assert response.status_code == 200 and '1 atualizados' in response.get_json()['mensagem']
    assert Resultado.query.one().gols_casa_real == 2


def test_sincronizacao_valida_dados(gestao):
    client, jogo = gestao
    url = '/interface/api/campeonato/sincronizar'
    assert client.post(url, json={'acao': 'outra', 'token': 't'}).status_code == 400
    assert client.post(url, json={'acao': 'jogos', 'token': 't'}).status_code == 400  # sem rodada nem completo


def test_limiter_bloqueia_decima_primeira_tentativa(monkeypatch):
    from app import create_app
    from config import TestingConfig
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_ENABLED', True)
    app = create_app('testing')
    client = app.test_client()
    tentativas = [client.post('/login', data={'email': 'x@example.com', 'senha': 'errada'}).status_code for _ in range(11)]
    assert tentativas == [302] * 10 + [429]


def test_limiter_recebe_uri_configurada(monkeypatch):
    from app import create_app
    from config import TestingConfig
    import flask_limiter._extension as extension
    original = extension.storage_from_string
    recebidas = []
    def registrar(uri, **kwargs):
        recebidas.append(uri)
        return original(uri, **kwargs)
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_STORAGE_URI', 'memory://regressao')
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_ENABLED', True)
    monkeypatch.setattr(extension, 'storage_from_string', registrar)
    create_app('testing')
    assert recebidas == ['memory://regressao']


def test_producao_selecionada_sem_flask_env(monkeypatch, tmp_path):
    from app import create_app
    from config import ProductionConfig
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.delenv('FLASK_ENV', raising=False)
    monkeypatch.setenv('FLASK_DEBUG', '0')
    monkeypatch.setattr(ProductionConfig, 'SECRET_KEY', 'chave-de-teste-exclusiva')
    # Este teste verifica seleção/cookies; Redis é validado em testes próprios.
    monkeypatch.setattr(ProductionConfig, 'RATELIMIT_ENABLED', False, raising=False)
    monkeypatch.setenv('PERSISTENT_DATA_DIR', str(tmp_path))
    app = create_app(database_uri='sqlite:///' + (tmp_path / 'banco.db').as_posix(), initialize_database=True)
    assert app.config['PRODUCTION'] and app.config['SESSION_COOKIE_SECURE']
    assert not app.debug


def test_chave_padrao_recusada_pela_configuracao_producao(monkeypatch):
    from app import create_app
    from config import ProductionConfig
    monkeypatch.setattr(ProductionConfig, 'SECRET_KEY', 'dev-inseguro-troque-em-producao')
    with pytest.raises(ValueError, match='desenvolvimento em produção'):
        create_app('production', database_uri='sqlite:///:memory:')


def test_ranking_consultas_nao_crescem_por_pessoa_ou_jogo(gestao):
    client, jogo = gestao
    bolao = Bolao.query.one()
    def adicionar(numero):
        pessoa = Participacao(bolao=bolao, nome_exibicao=f'Pessoa {numero}')
        novo = Jogo(time_casa=f'Casa {numero}', time_fora='Fora', rodada=jogo.rodada)
        db.session.add_all([Resultado(jogo=novo, gols_casa_real=1, gols_fora_real=0),
                           Palpite(participacao=pessoa, jogo=novo, gols_casa=1, gols_fora=0)])
        db.session.commit()
    def contar():
        db.session.expire_all()
        g.pop('_login_user', None)
        consultas = []
        def capturar(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                consultas.append(statement)
        event.listen(db.engine, 'before_cursor_execute', capturar)
        try:
            response = client.get(f'/interface/api/boloes/{bolao.id}/classificacao')
            assert response.status_code == 200
        finally:
            event.remove(db.engine, 'before_cursor_execute', capturar)
        return len(consultas)
    adicionar(0)
    antes = contar()
    for i in range(1, 9):
        adicionar(i)
    assert contar() <= antes + 1
