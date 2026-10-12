from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Entre na sua conta para continuar."
login_manager.login_message_category = "info"
csrf = CSRFProtect()

# Instância única do Limiter; inicializada em create_app() via init_app.
# Usa a configuração de armazenamento definida em config.py
# (RATELIMIT_STORAGE_URI) — evita criar múltiplas instâncias.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
)
