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
def _responsavel_logado():
    """Quem já entrou com senha não precisa do limite geral anti-robô."""
    from flask_login import current_user
    return current_user.is_authenticated


# Limites pensados para o Render Free (1 processo, contadores em memória):
# - visitantes sem login: 1000 requisições/hora por IP (antes 50/hora e 200/dia,
#   o que bloqueava o uso normal, inclusive várias pessoas na mesma rede 4G);
# - responsáveis logados: sem limite geral; a API da interface tem um teto
#   próprio só contra laços acidentais (routes/api.py);
# - login e cadastro continuam com limites baixos contra tentativa de senha.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    default_limits_exempt_when=_responsavel_logado,
)
