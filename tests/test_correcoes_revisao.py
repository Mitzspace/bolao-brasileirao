"""Regressões dos defeitos reproduzidos na revisão de 12/10/2026."""
from datetime import datetime
from io import BytesIO

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
    response = client.post('/admin/resultados', data={
        'jogo_id': jogo.id, 'gols_casa_real': valor, 'gols_fora_real': '0'})
    assert response.status_code == 400
    assert Resultado.query.count() == 0


@pytest.mark.parametrize('editar', [False, True])
@pytest.mark.parametrize('campo,valor', [('data', 'invalida'), ('time_casa', ''), ('rodada_id', '')])
def test_jogo_invalido_preserva_dados(gestao, editar, campo, valor):
    client, jogo = gestao
    dados = dict(time_casa='Novo time', time_fora='Outro', rodada_id=jogo.rodada_id, data='2026-12-10T12:00')
    dados[campo] = valor
    url = f'/admin/jogo/{jogo.id}/editar' if editar else '/admin/jogo'
    response = client.post(url, data=dados)
    assert response.status_code == 400
    db.session.refresh(jogo)
    assert jogo.time_casa == 'Time A'
    assert Jogo.query.count() == 1


def test_campeonato_e_rodada_invalidos(gestao):
    client, jogo = gestao
    assert client.post('/admin/campeonato', data={'nome': 'Teste', 'ano': 'abc'}).status_code == 400
    assert client.post('/admin/rodada', data={'nome': ''}).status_code == 400
    assert Campeonato.query.count() == 1
    assert Rodada.query.count() == 1


def test_resultado_valido_inclui_zero(gestao):
    client, jogo = gestao
    assert client.post('/admin/resultados', data={
        'jogo_id': jogo.id, 'gols_casa_real': '0', 'gols_fora_real': '1'}).status_code == 302
    assert Resultado.query.one().gols_casa_real == 0


def test_importacao_api_atualiza_existente_e_cria_novo(gestao, monkeypatch):
    client, jogo = gestao
    jogo.external_fonte, jogo.external_id = 'football-data.org', '10'
    db.session.commit()
    g.pop('_login_user', None)
    data = datetime(2026, 12, 10, 12)
    itens = [dict(external_id=id, time_casa='A', time_fora='B', data=data) for id in ['10', '11']]
    monkeypatch.setattr('routes.admin.buscar_jogos_football_data', lambda **kwargs: itens)
    dados = dict(token='teste', campeonato_id=jogo.rodada.campeonato_id,
                 nome_rodada=jogo.rodada.nome, competicao='BSA')
    for _ in range(2):
        response = client.post('/admin/importar-jogos', data=dados)
        assert response.status_code == 302
        assert 'login' not in response.location, response.location
    assert Jogo.query.count() == 2
    db.session.refresh(jogo)
    assert jogo.data == data


def test_importacao_resultados_api(gestao, monkeypatch):
    client, jogo = gestao
    jogo.external_fonte, jogo.external_id = 'football-data.org', '10'
    db.session.commit()
    g.pop('_login_user', None)
    monkeypatch.setattr('routes.admin.buscar_resultados_football_data', lambda **kwargs: [
        dict(external_id='10', gols_casa_real=2, gols_fora_real=1, data=None)])
    response = client.post('/admin/importar-resultados', data={'token': 'teste', 'competicao': 'BSA'})
    assert response.status_code == 302
    assert 'login' not in response.location, response.location
    assert Resultado.query.one().gols_casa_real == 2


def test_planilha_falha_sem_expor_erro_ou_criar_campeonato(gestao, monkeypatch):
    client, jogo = gestao
    def falhar(*args, **kwargs):
        raise RuntimeError('SEGREDO_INTERNO caminho privado')
    monkeypatch.setattr('services.importador_planilha.importar_planilha_bolao', falhar)
    response = client.post('/admin/importar-planilha', data={
        'campeonato_id': jogo.rodada.campeonato_id,
        'arquivo': (BytesIO(b'invalido'), '../../arquivo.xlsx')}, follow_redirects=True)
    assert response.status_code == 200
    assert b'SEGREDO_INTERNO' not in response.data
    assert 'Confira o formato' in response.text
    assert Campeonato.query.count() == 1


def test_planilha_local_fora_da_pasta_recusada(gestao, tmp_path, monkeypatch):
    client, jogo = gestao
    monkeypatch.setenv('DOWNLOADS_FOLDER', str(tmp_path / 'downloads'))
    fora = tmp_path / 'privado.xlsx'
    fora.write_bytes(b'privado')
    response = client.post('/admin/importar-planilha', data={
        'campeonato_id': jogo.rodada.campeonato_id, 'planilha_local': str(fora)}, follow_redirects=True)
    assert 'selecione uma planilha existente' in response.text


def test_palpite_lote_invalido_nao_grava_parcialmente(gestao):
    client, jogo = gestao
    segundo = Jogo(time_casa='C', time_fora='D', rodada=jogo.rodada)
    db.session.add(segundo)
    db.session.commit()
    g.pop('_login_user', None)
    dados = {f'casa_{jogo.id}': '2', f'fora_{jogo.id}': '1',
             f'casa_{segundo.id}': '-1', f'fora_{segundo.id}': '0'}
    response = client.post(f'/rodada/{jogo.rodada_id}', data=dados)
    assert response.status_code == 302
    assert '/rodada/' in response.location
    assert Palpite.query.count() == 0


def test_limiter_bloqueia_decima_primeira_tentativa(monkeypatch):
    from app import create_app
    from config import TestingConfig
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_ENABLED', True)
    app = create_app('testing')
    client = app.test_client()
    assert [client.get('/login').status_code for _ in range(11)] == [200] * 10 + [429]


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
            response = client.get('/ranking')
            assert response.status_code == 200, response.location
        finally:
            event.remove(db.engine, 'before_cursor_execute', capturar)
        return len(consultas)
    adicionar(0)
    antes = contar()
    for i in range(1, 9):
        adicionar(i)
    assert contar() <= antes + 1


@pytest.mark.parametrize('url,dados', [('/admin/campeonato', {'nome':'Solto','ano':2026}),
    ('/admin/importar-planilha', {'novo_campeonato_nome':'Solto','novo_campeonato_ano':2026})])
def test_campeonato_independente_recusado(gestao, url, dados):
    client, jogo = gestao
    dados = dict(dados, arquivo=(BytesIO(b'invalido'), 'dados.xlsx'))
    antes = Campeonato.query.count()
    assert client.post(url, data=dados).status_code == 400
    assert Campeonato.query.count() == antes
