"""Testes reais opcionais: TEST_POSTGRES_URL deve apontar a cluster local descartável."""
from copy import deepcopy
from datetime import datetime
import os
import uuid

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url

from app import create_app
from config import normalizar_database_url
from database import db
from migrations.sqlite_para_postgres import carregar_snapshot, converter, ErroMigracao, importar, resumo
from models import (Bolao, BonusRodada, Campeonato, ClassificacaoCache, Jogo, Participacao,
                    Participante, Palpite, PalpiteLog, Resultado, Rodada)
from services.operacao import backup_sqlite
from utils import hash_senha


@pytest.fixture
def sqlite_atual(tmp_path):
    path = tmp_path / 'origem.db'
    app = create_app('testing', database_uri='sqlite:///' + path.as_posix())
    with app.app_context():
        pessoa = Participante(id=37, nome='José administrador', email='admin@example.com',
            senha=hash_senha('Senha-forte-123'), admin=True, admin_global=True)
        camp = Campeonato(nome='Brasileirão', ano=2030)
        rodada = Rodada(nome='Rodada 1', campeonato=camp)
        jogo = Jogo(rodada=rodada, time_casa='São Paulo', time_fora='Flamengo', data=datetime(2030, 6, 1, 20))
        bolao = Bolao(nome='Bolão de teste', campeonato=camp, criador=pessoa)
        part = Participacao(bolao=bolao, usuario=pessoa, participante_legado=pessoa,
            nome_exibicao=pessoa.nome, papel='responsavel', rodada_entrada=rodada)
        db.session.add_all([pessoa, camp, rodada, jogo, bolao, part])
        db.session.commit()
        db.session.add_all([
            Palpite(participacao=part, participante_id=pessoa.id, jogo=jogo, gols_casa=2, gols_fora=1),
            Resultado(jogo=jogo, gols_casa_real=2, gols_fora_real=1),
            BonusRodada(participacao=part, participante=pessoa, rodada=rodada, pontos=3),
            ClassificacaoCache(campeonato=camp, dados_json='{"nome":"São Paulo"}')])
        db.session.commit()
        db.session.remove()
        db.engine.dispose()
    return path


@pytest.fixture
def pg_engine():
    raw = os.environ.get('TEST_POSTGRES_URL')
    if not raw:
        pytest.skip('PostgreSQL local não configurado; configure TEST_POSTGRES_URL.')
    url = make_url(normalizar_database_url(raw))
    assert url.host in {'127.0.0.1', 'localhost'}, 'Testes só podem criar bancos em PostgreSQL local.'
    nome = 'bolao_test_' + uuid.uuid4().hex
    admin = create_engine(url, isolation_level='AUTOCOMMIT')
    with admin.connect() as con:
        con.execute(text(f'CREATE DATABASE "{nome}"'))
    engine = create_engine(url.set(database=nome))
    try:
        yield engine
    finally:
        engine.dispose()
        # Cluster descartável: bancos isolados ficam para inspeção até encerrá-lo.
        # Não há DROP DATABASE em credenciais fornecidas ao teste.
        admin.dispose()


def test_snapshot_preserva_e_valida(sqlite_atual, tmp_path):
    original = sqlite_atual.read_bytes()
    copia = tmp_path / 'backup.db'
    backup_sqlite(sqlite_atual, copia)
    dados = carregar_snapshot(copia)
    assert dados['participante'][0]['admin_global'] is True
    assert dados['participante'][0]['id'] == 37
    assert dados['palpite_log'] and dados['participacao_log']
    assert sqlite_atual.read_bytes() == original
    with pytest.raises(ErroMigracao, match='booleano'):
        converter(Participante.__table__.c.admin, 3)
    with pytest.raises(ErroMigracao, match='texto'):
        converter(Participante.__table__.c.nome, 'x' * 101)


def test_importacao_postgres_login_gestao_sequencias(sqlite_atual, pg_engine):
    dados = carregar_snapshot(sqlite_atual)
    assert importar(dados, pg_engine) == resumo(dados)
    with pytest.raises(ErroMigracao, match='não vazio'):
        importar(dados, pg_engine)
    app = create_app('testing', database_uri=pg_engine.url.render_as_string(hide_password=False))
    client = app.test_client()
    assert client.post('/login', data={'email': 'admin@example.com', 'senha': 'Senha-forte-123'}).status_code == 302
    for rota in ['gestao', 'ranking', 'participantes', 'palpites', 'resultados']:
        assert client.get('/b/1/' + rota).status_code == 200, rota
    with app.app_context():
        novo = Participante(nome='Novo admin', email='novo@example.com', admin_global=True)
        db.session.add(novo)
        db.session.commit()
        assert novo.id == 38
        antes = PalpiteLog.query.count()
    response = client.post('/b/1/palpites', data={'participante_id': '1', 'rodada_id': '1', 'casa_1': '3', 'fora_1': '1'})
    assert response.status_code == 302
    with app.app_context():
        assert Palpite.query.one().gols_casa == 3
        assert PalpiteLog.query.count() > antes
        db.session.remove()
        db.engine.dispose()
    # Nova factory/redeploy não apaga dados nem cria novo banco.
    again = create_app('testing', database_uri=pg_engine.url.render_as_string(hide_password=False))
    with again.app_context():
        assert Participante.query.count() == 2 and Palpite.query.one().gols_casa == 3
        db.session.remove()
        db.engine.dispose()


def test_postgres_reverte_ddl_e_registros_na_falha(sqlite_atual, pg_engine):
    dados = carregar_snapshot(sqlite_atual)
    ruim = deepcopy(dados)
    ruim['palpite'][0]['gols_casa'] = -1  # CHECK após várias tabelas já copiadas.
    with pytest.raises(Exception):
        importar(ruim, pg_engine)
    assert inspect(pg_engine).get_table_names() == []
    assert importar(dados, pg_engine) == resumo(dados)


def test_postgres_schema_parcial_nao_e_modificado(pg_engine):
    with pg_engine.begin() as con:
        con.execute(text('CREATE TABLE outra_tabela (id INTEGER PRIMARY KEY)'))
    with pytest.raises(RuntimeError, match='Schema PostgreSQL incompleto'):
        create_app('testing', database_uri=pg_engine.url.render_as_string(hide_password=False))
    assert inspect(pg_engine).get_table_names() == ['outra_tabela']
