import sqlite3
from unittest.mock import Mock

import pytest
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from database import db
from models import Participante
from services.operacao import backup_sqlite


def test_producao_recusa_banco_efemero(monkeypatch, tmp_path):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(PRODUCTION=True, SECRET_KEY='chave-teste', RATELIMIT_ENABLED=False)
    monkeypatch.setenv('PERSISTENT_DATA_DIR', str(tmp_path))
    with pytest.raises(ValueError, match='disco persistente'):
        Config.init_app(app)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + (tmp_path / 'banco.db').as_posix()
    Config.init_app(app)


def test_health_sem_banco_e_ready_falha_backend(app, monkeypatch):
    client = app.test_client()
    for _ in range(55):
        assert client.get('/healthz').status_code == 200
    app.config['RATELIMIT_ENABLED'] = True
    monkeypatch.setattr('extensions.limiter._storage', Mock(check=Mock(side_effect=RuntimeError('segredo'))))
    response = client.get('/readyz')
    assert response.status_code == 503
    assert b'segredo' not in response.data
    assert client.get('/healthz').status_code == 200


def test_admin_terminal_e_backup(app, tmp_path):
    result = app.test_cli_runner().invoke(args=['criar-admin', '--email', 'admin@example.com',
        '--nome', 'Admin'], input='uma-senha-longa-123\numa-senha-longa-123\n')
    assert result.exit_code == 0, result.output
    with app.app_context():
        usuario = Participante.query.one()
        assert usuario.admin_global and usuario.conta_ativa
        assert usuario.senha != 'uma-senha-longa-123'
    origem, destino = tmp_path / 'original.db', tmp_path / 'backup.db'
    with sqlite3.connect(origem) as con:
        con.execute('CREATE TABLE dados (id INTEGER)')
        con.execute('INSERT INTO dados VALUES (42)')
    backup_sqlite(origem, destino)
    with sqlite3.connect(destino) as con:
        assert con.execute('SELECT id FROM dados').fetchone()[0] == 42
    with pytest.raises(FileExistsError):
        backup_sqlite(origem, destino)


def test_proxy_https_e_cabecalhos(monkeypatch):
    from app import create_app
    from config import TestingConfig
    monkeypatch.setattr(TestingConfig, 'TRUST_PROXY', True)
    app = create_app('testing')
    assert isinstance(app.wsgi_app, ProxyFix)
    @app.get('/test-proxy')
    def proxy():
        return {'ip': request.remote_addr, 'https': request.is_secure, 'host': request.host}
    response = app.test_client().get('/test-proxy', headers={
        'X-Forwarded-For': '198.51.100.1, 203.0.113.5',
        'X-Forwarded-Proto': 'https', 'X-Forwarded-Host': 'evil.example'})
    assert response.json == {'ip': '203.0.113.5', 'https': True, 'host': 'localhost'}
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
