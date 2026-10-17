import os
import secrets
from datetime import timedelta
from urllib.parse import urlsplit


def normalizar_database_url(valor, exigir_tls=False):
    """Aceita URLs Neon/libpq e seleciona psycopg 3 sem perder parâmetros."""
    from sqlalchemy.engine import make_url
    try:
        url = make_url(valor)
    except Exception:
        raise ValueError('DATABASE_URL inválida.') from None
    if url.drivername in {'postgres', 'postgresql', 'postgresql+psycopg'}:
        url = url.set(drivername='postgresql+psycopg')
        if exigir_tls:
            if url.query.get('sslmode', 'require') not in {'require', 'verify-ca', 'verify-full'}:
                raise ValueError('PostgreSQL em produção exige TLS (sslmode=require ou verify-full).')
            url = url.update_query_dict({'sslmode': url.query.get('sslmode', 'require')})
    return url.render_as_string(hide_password=False)


def uri_rate_limit(ambiente=None):
    """Prioriza a configuração específica; aceita a URL fornecida pela hospedagem."""
    ambiente = os.environ if ambiente is None else ambiente
    for nome in ('RATELIMIT_STORAGE_URI', 'RATELIMIT_STORAGE_URL', 'REDIS_URL'):
        valor = ambiente.get(nome, '').strip()
        if valor:
            return valor
    return 'memory://'


class Config:
    """Configuração base da aplicação."""

    SECRET_KEY = os.environ.get("SECRET_KEY", None)

    # Segurança de sessão (base)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_REFRESH_EACH_REQUEST = True
    # "Manter conectado" no login (Flask-Login): cookie próprio, só HTTP, por 30 dias.
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    PRODUCTION = False
    RATELIMIT_SINGLE_PROCESS = os.environ.get('RATELIMIT_SINGLE_PROCESS', 'false').lower() == 'true'
    # Ativar apenas atrás do proxy HTTPS da hospedagem.
    TRUST_PROXY = os.environ.get('TRUST_PROXY', 'false').lower() == 'true'
    TRUSTED_HOSTS = [h.strip() for h in os.environ.get('TRUSTED_HOSTS', '').split(',') if h.strip()] or None

    @staticmethod
    def init_app(app):
        """Valida configurações críticas na inicialização."""
        if not app.config['SECRET_KEY']:
            raise ValueError(
                "SECRET_KEY não está definido. Defina a variável de ambiente SECRET_KEY "
                "ou gere uma chave segura com: python -c 'import secrets; print(secrets.token_hex(32))'"
            )

        # Valida que a SECRET_KEY não é a padrão de desenvolvimento em produção
        is_production = app.config['PRODUCTION']
        if is_production and app.config['SECRET_KEY'] == "dev-inseguro-troque-em-producao":
            raise ValueError(
                "Usando SECRET_KEY de desenvolvimento em produção. "
                "Defina uma SECRET_KEY segura na variável de ambiente."
            )

        uri = app.config['RATELIMIT_STORAGE_URI']
        try:
            esquema = urlsplit(uri).scheme
        except ValueError:
            raise ValueError('RATELIMIT_STORAGE_URI inválida.') from None
        if (is_production and app.config.get('RATELIMIT_ENABLED', True) and esquema == 'memory'
                and not app.config['RATELIMIT_SINGLE_PROCESS']):
            raise ValueError(
                'Use armazenamento compartilhado ou RATELIMIT_SINGLE_PROCESS=true '
                'com exatamente um worker para limites em memória.'
            )
        if esquema in {'redis', 'rediss'}:
            app.config['RATELIMIT_STORAGE_OPTIONS'] = {
                'socket_connect_timeout': 3,
                'socket_timeout': 3,
                **app.config.get('RATELIMIT_STORAGE_OPTIONS', {}),
            }

        app.config['SQLALCHEMY_DATABASE_URI'] = normalizar_database_url(
            app.config['SQLALCHEMY_DATABASE_URI'], exigir_tls=is_production)
        from sqlalchemy.engine import make_url
        url = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
        if url.get_backend_name() == 'postgresql':
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'hide_parameters': True,
                'pool_pre_ping': True, 'pool_recycle': 300,
                'pool_size': 2, 'max_overflow': 2, 'pool_timeout': 15,
                'connect_args': {'connect_timeout': 15, 'prepare_threshold': None},
            }
        if is_production:
            from pathlib import Path
            if url.get_backend_name() == 'sqlite':
                pasta = os.environ.get('PERSISTENT_DATA_DIR', '')
                banco = Path(url.database or '')
                if not pasta or not banco.is_absolute() or not banco.resolve().is_relative_to(Path(pasta).resolve()):
                    raise ValueError('SQLite em produção requer DATABASE_URL absoluta dentro de PERSISTENT_DATA_DIR em disco persistente.')
                if not Path(pasta).is_dir():
                    raise ValueError('PERSISTENT_DATA_DIR não existe; monte o disco persistente antes de iniciar.')

        # Define UPLOAD_FOLDER de forma confiável usando app.instance_path
        app.config["UPLOAD_FOLDER"] = os.path.join(
            os.environ.get('PERSISTENT_DATA_DIR') or app.instance_path, "uploads"
        )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///banco.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Token da API football-data.org (opcional: pode informar via interface admin também)
    FOOTBALL_DATA_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "")

    # Rate limiting
    # Aceita o nome antigo durante a transição, mas expõe a chave da extensão.
    RATELIMIT_STORAGE_URI = uri_rate_limit()
    RATELIMIT_KEY_PREFIX = os.environ.get('RATELIMIT_KEY_PREFIX', 'bolao2')
    # Se Redis falhar, não contorna os limites com contadores locais por processo.
    RATELIMIT_IN_MEMORY_FALLBACK_ENABLED = False
    RATELIMIT_SWALLOW_ERRORS = False
    RATELIMIT_STRATEGY = "fixed-window"

    # Upload de arquivos
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {"xlsx"}

    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento."""
    TEMPLATES_AUTO_RELOAD = True
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
    # Em desenvolvimento, usa uma chave aleatória se não definida
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))


class ProductionConfig(Config):
    """Configuração para produção."""
    DEBUG = False
    PRODUCTION = True
    # Em produção, SECRET_KEY é obrigatório via variável de ambiente
    SECRET_KEY = os.environ.get("SECRET_KEY")
    WTF_CSRF_SSL_ONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True


class TestingConfig(Config):
    """Configuração para testes."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    # Desativa rate limiting durante testes para não interferir
    RATELIMIT_ENABLED = False
    SECRET_KEY = "test-secret-key-not-for-production"


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}
