from datetime import datetime
from unittest.mock import Mock

import pytest
from flask import Flask
from sqlalchemy.engine import make_url

from config import Config, normalizar_database_url


@pytest.mark.parametrize('prefixo', ['postgres://', 'postgresql://', 'postgresql+psycopg://'])
def test_url_neon_preserva_credenciais_e_tls(prefixo):
    url = make_url(normalizar_database_url(prefixo + 'user:p%40ss@db.example/bolao?sslmode=require&channel_binding=require', True))
    assert url.drivername == 'postgresql+psycopg'
    assert url.password == 'p@ss'
    assert url.query['sslmode'] == url.query['channel_binding'] == 'require'


def test_producao_recusa_postgres_sem_tls():
    with pytest.raises(ValueError, match='TLS'):
        normalizar_database_url('postgresql://host/db?sslmode=disable', True)


def test_limiter_memoria_explicitamente_permitido():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(SECRET_KEY='teste', PRODUCTION=True, RATELIMIT_SINGLE_PROCESS=True,
        RATELIMIT_STORAGE_URI='memory://', SQLALCHEMY_DATABASE_URI='postgresql://localhost/test')
    Config.init_app(app)
    assert app.config['SQLALCHEMY_ENGINE_OPTIONS']['pool_pre_ping']
    assert app.config['SQLALCHEMY_ENGINE_OPTIONS']['pool_size'] == 2


def test_login_ainda_limitado_sem_redis(monkeypatch):
    from app import create_app
    from config import TestingConfig
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_ENABLED', True)
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_STORAGE_URI', 'memory://')
    app = create_app('testing')
    client = app.test_client()
    for _ in range(10):
        assert client.post('/login', data={'email': 'bad@example.com', 'senha': 'invalid'}).status_code == 302
    assert client.post('/login', data={'email': 'bad@example.com', 'senha': 'invalid'}).status_code == 429


def test_relogio_brasilia_independente_do_servidor(monkeypatch):
    from services import relogio
    mock = Mock()
    mock.now.return_value = datetime.fromisoformat('2030-01-01T12:00:00-03:00')
    monkeypatch.setattr(relogio, 'datetime', mock)
    assert relogio.agora_brasilia() == datetime(2030, 1, 1, 12)
    assert str(mock.now.call_args.args[0]) == 'America/Sao_Paulo'


def test_producao_nunca_inicializa_banco_sozinha(monkeypatch, tmp_path):
    import sqlite3
    from app import create_app
    from config import ProductionConfig
    monkeypatch.setattr(ProductionConfig, 'SECRET_KEY', 'chave-privada-apenas-do-teste')
    monkeypatch.setattr(ProductionConfig, 'RATELIMIT_STORAGE_URI', 'memory://')
    monkeypatch.setattr(ProductionConfig, 'RATELIMIT_SINGLE_PROCESS', True)
    monkeypatch.setenv('PERSISTENT_DATA_DIR', str(tmp_path))
    path = tmp_path / 'producao.db'
    with pytest.raises(RuntimeError, match='não inicializado'):
        create_app('production', database_uri='sqlite:///' + path.as_posix())
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 0
