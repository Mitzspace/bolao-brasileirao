from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask

from config import Config, uri_rate_limit
from services.diagnostico_limiter import registrar_comando


def configuracao(uri, producao=True):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(SECRET_KEY='chave-exclusiva-de-teste', PRODUCTION=producao,
                      SQLALCHEMY_DATABASE_URI='postgresql://localhost/test',
                      RATELIMIT_STORAGE_URI=uri)
    return app


@pytest.mark.parametrize('ambiente,esperado', [
    ({}, 'memory://'),
    ({'REDIS_URL': 'rediss://redis.example:6380/0'}, 'rediss://redis.example:6380/0'),
    ({'REDIS_URL': 'redis://redis.example/0', 'RATELIMIT_STORAGE_URI': '  '}, 'redis://redis.example/0'),
    ({'REDIS_URL': 'redis://padrao/0', 'RATELIMIT_STORAGE_URL': 'redis://legado/1'}, 'redis://legado/1'),
    ({'RATELIMIT_STORAGE_URI': 'redis://novo/2', 'RATELIMIT_STORAGE_URL': 'redis://legado/1'}, 'redis://novo/2'),
])
def test_prioridade_das_urls(ambiente, esperado):
    assert uri_rate_limit(ambiente) == esperado


def test_producao_recusa_memoria():
    app = configuracao('memory://')
    with pytest.raises(ValueError, match='armazenamento compartilhado'):
        Config.init_app(app)


def test_desenvolvimento_permite_memoria():
    Config.init_app(configuracao('memory://', producao=False))


@pytest.mark.parametrize('uri', ['redis://localhost:6379/0', 'rediss://redis.example:6380/0'])
def test_redis_configura_timeouts_sem_conectar(uri):
    app = configuracao(uri)
    Config.init_app(app)
    assert app.config['RATELIMIT_STORAGE_OPTIONS'] == dict(socket_connect_timeout=3, socket_timeout=3)
    assert app.config['RATELIMIT_IN_MEMORY_FALLBACK_ENABLED'] is False
    assert app.config['RATELIMIT_SWALLOW_ERRORS'] is False


@pytest.mark.parametrize('resposta,exit_code', [(True, 0), (False, 1)])
def test_comando_verifica_backend(monkeypatch, resposta, exit_code):
    app = configuracao('redis://redis.example/0')
    storage = SimpleNamespace(check=Mock(return_value=resposta))
    monkeypatch.setattr('services.diagnostico_limiter.limiter', SimpleNamespace(storage=storage))
    registrar_comando(app)
    result = app.test_cli_runner().invoke(args=['verificar-limiter'])
    assert result.exit_code == exit_code
    storage.check.assert_called_once_with()


def test_comando_nao_expoe_credenciais(monkeypatch):
    segredo = 'rediss://usuario:senha-secreta@privado.example:6380/0'
    app = configuracao(segredo)
    storage = SimpleNamespace(check=Mock(side_effect=RuntimeError(segredo)))
    monkeypatch.setattr('services.diagnostico_limiter.limiter', SimpleNamespace(storage=storage))
    registrar_comando(app)
    result = app.test_cli_runner().invoke(args=['verificar-limiter'])
    assert result.exit_code == 1
    assert 'Confira o serviço' in result.output
    assert 'senha-secreta' not in result.output and 'privado.example' not in result.output


@pytest.mark.parametrize('habilitado', [True, False])
def test_comando_recusa_memoria_ou_limiter_desativado(monkeypatch, habilitado):
    app = configuracao('memory://', producao=False)
    app.config['RATELIMIT_ENABLED'] = habilitado
    storage = SimpleNamespace(check=Mock())
    monkeypatch.setattr('services.diagnostico_limiter.limiter', SimpleNamespace(storage=storage))
    registrar_comando(app)
    assert app.test_cli_runner().invoke(args=['verificar-limiter']).exit_code == 1
    storage.check.assert_not_called()
