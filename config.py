import os
import secrets


class Config:
    """Configuração base da aplicação."""

    SECRET_KEY = os.environ.get("SECRET_KEY", None)

    @staticmethod
    def init_app(app):
        """Valida configurações críticas na inicialização."""
        if not app.config['SECRET_KEY']:
            raise ValueError(
                "SECRET_KEY não está definido. Defina a variável de ambiente SECRET_KEY "
                "ou gere uma chave segura com: python -c 'import secrets; print(secrets.token_hex(32))'"
            )

        # Valida que a SECRET_KEY não é a padrão de desenvolvimento em produção
        if (os.environ.get("FLASK_ENV") == "production" or
            os.environ.get("FLASK_DEBUG") == "0"):
            if app.config['SECRET_KEY'] == "dev-inseguro-troque-em-producao":
                raise ValueError(
                    "Usando SECRET_KEY de desenvolvimento em produção. "
                    "Defina uma SECRET_KEY segura na variável de ambiente."
                )

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///banco.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Token da API football-data.org (opcional: pode informar via interface admin também)
    FOOTBALL_DATA_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "")

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")
    RATELIMIT_STRATEGY = "fixed-window"

    # Upload de arquivos
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "instance", "uploads")
    ALLOWED_EXTENSIONS = {"xlsx", "xls"}

    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None


class DevelopmentConfig(Config):
    """Configuração para desenvolvimento."""
    DEBUG = True
    # Em desenvolvimento, usa uma chave aleatória se não definida
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))


class ProductionConfig(Config):
    """Configuração para produção."""
    DEBUG = False
    # Em produção, SECRET_KEY é obrigatório via variável de ambiente
    SECRET_KEY = os.environ.get("SECRET_KEY")
    WTF_CSRF_SSL_ONLY = True


class TestingConfig(Config):
    """Configuração para testes."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
}
