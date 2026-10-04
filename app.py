import os
from flask import Flask, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFError

# Carrega variáveis de ambiente do arquivo .env (se existir)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import config
from database import db
from extensions import login_manager
from models import Participante


def create_app(config_name=None):
    """Factory pattern para criar a aplicação Flask."""

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Valida configurações críticas
    config[config_name].init_app(app)

    # Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)

    # Inicializa rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )

    @login_manager.user_loader
    def load_user(user_id):
        return Participante.query.get(int(user_id))

    from routes.auth import auth
    from routes.admin import admin
    from routes.participante import participante

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(participante)

    @app.errorhandler(403)
    def acesso_negado(e):
        return render_template("403.html"), 403

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return render_template("429.html"), 429

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template("403.html"), 403

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
