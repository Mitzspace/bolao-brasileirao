import os
from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

# Carrega variáveis de ambiente do arquivo .env (se existir)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from config import config
from database import db
from extensions import csrf, login_manager, limiter
from models import Participante


def create_app(config_name=None, database_uri=None, initialize_database=False):
    """Factory pattern para criar a aplicação Flask."""

    if config_name is None:
        config_name = (os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV")
                       or ("development" if os.environ.get("FLASK_DEBUG") == "1" else "production"))

    if config_name not in config:
        raise ValueError("APP_ENV inválido. Use development, production ou testing.")

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    if database_uri is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri

    # Valida configurações críticas
    config[config_name].init_app(app)

    if app.config['TRUST_PROXY']:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=0, x_port=0, x_prefix=0)

    @app.after_request
    def cabecalhos_seguranca(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if app.config['PRODUCTION']:
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
        return response

    # Inicializa extensões
    from services.acesso import restringir_acesso_participante
    # Rotas desativadas retornam 404 também em POST, antes da validação CSRF.
    app.before_request(restringir_acesso_participante)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Inicializa rate limiting (usa RATELIMIT_STORAGE_URI do config)
    limiter.init_app(app)
    from services.diagnostico_limiter import registrar_comando
    registrar_comando(app)
    from services.operacao import registrar_comandos
    registrar_comandos(app)

    @app.get('/healthz')
    @limiter.exempt
    def healthz():
        # Sondas frequentes não devem acordar o Neon nem consumir compute.
        return {'status': 'ok'}

    @app.get('/readyz')
    @limiter.exempt
    def readyz():
        from sqlalchemy import text
        try:
            db.session.execute(text('SELECT 1'))
            if app.config.get('RATELIMIT_ENABLED', True) and not limiter.storage.check():
                return {'status': 'unavailable'}, 503
        except Exception:
            db.session.rollback()
            return {'status': 'unavailable'}, 503
        return {'status': 'ok'}

    @login_manager.user_loader
    def load_user(user_id):
        user = db.session.get(Participante, int(user_id))
        return user if user and user.conta_ativa else None

    from services import auditoria  # registra auditoria transacional dos escritores existentes
    from services.regras_pontuacao import REGRAS_PONTUACAO
    from services.escudos import escudo_time
    app.jinja_env.globals['escudo_time'] = escudo_time

    @app.context_processor
    def regras_pontuacao():
        return {"regras_pontuacao": REGRAS_PONTUACAO}

    from routes.auth import auth
    from routes.admin import admin
    from routes.participante import participante

    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(participante)

    from services.urls_bolao import registrar_urls_bolao, redirecionar_url_antiga
    registrar_urls_bolao(app)

    from services.contexto_bolao import carregar_contexto, contexto_templates, contexto_nas_urls
    app.before_request(carregar_contexto)
    app.before_request(redirecionar_url_antiga)
    app.context_processor(contexto_templates)
    app.url_defaults(contexto_nas_urls)

    @app.errorhandler(403)
    def acesso_negado(e):
        return render_template("403.html"), 403

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return render_template("429.html"), 429

    @app.errorhandler(409)
    def conflito_gestao(e):
        return render_template('conflito_gestao.html', mensagem=e.description), 409

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template("403.html"), 403

    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if db.engine.dialect.name == 'postgresql' and inspector.get_table_names():
            tabelas_pg = set(inspector.get_table_names())
            if any(t.name not in tabelas_pg or not set(t.columns.keys()).issubset(
                    {c['name'] for c in inspector.get_columns(t.name)})
                   for t in db.metadata.sorted_tables):
                raise RuntimeError('Schema PostgreSQL incompleto. Prepare migração SQL explícita com backup; não execute os scripts legados SQLite neste banco.')
        if "participante" in inspector.get_table_names():
            obrigatorias = {
                "participante": {"admin_global", "conta_ativa"},
                "jogo": {"classico", "primeiro_marcador"},
                "palpite": {"participacao_id", "origem", "lancado_por", "recebido_em", "auditoria_legada"},
                "bonus_rodada": {"participacao_id", "historico"},
                "bolao": {"permite_palpite_proprio", "permite_lancamento_por_responsavel"},
                "participacao": {"usuario_id", "nome_exibicao", "papel", "status"},
                "palpite_log": {"valores_anteriores", "valores_novos"},
            }
            tabelas = set(inspector.get_table_names())
            if any(t not in tabelas or not campos.issubset({c["name"] for c in inspector.get_columns(t)})
                   for t, campos in obrigatorias.items()):
                raise RuntimeError("Banco anterior à Fase 1. Revise MIGRACAO_FASE1.md e execute a migração explícita com backup. O app não migra o banco automaticamente.")
            novos_campos = {
                "bolao": {"politica_entrada_tardia"},
                "participacao": {"rodada_entrada_id", "rodada_desistencia_id", "motivo_desistencia",
                    "desistencia_registrada_em", "desistencia_registrada_por", "observacao"},
                "palpite": {"excluido_por_desistencia"},
                "participacao_log": {"participacao_id", "alterado_por", "alterado_em", "acao",
                    "valores_anteriores", "valores_novos"},
            }
            if any(t not in tabelas or not campos.issubset({c["name"] for c in inspector.get_columns(t)})
                   for t, campos in novos_campos.items()):
                raise RuntimeError("Migração de participação pendente. Siga MIGRACAO_PARTICIPACAO.md; o banco não é migrado automaticamente.")
            if 'situacao' not in {c['name'] for c in inspector.get_columns('palpite')}:
                raise RuntimeError('Migração pendente: execute python -m migrations.situacao_palpite CAMINHO_DO_BANCO. Consulte AJUSTES_PALPITES_SYNC.md.')
        else:
            if app.config['PRODUCTION'] and not initialize_database:
                raise RuntimeError('Banco não inicializado. Execute python -m scripts.inicializar_banco ou migre o SQLite antes do deploy.')
            db.create_all()

        # Falha explícita em schemas parciais, sem ALTER/DROP ou reset no startup.
        if app.config['PRODUCTION']:
            inspector = inspect(db.engine)
            tabelas = set(inspector.get_table_names())
            if any(t.name not in tabelas or not set(t.columns.keys()).issubset(
                    {c['name'] for c in inspector.get_columns(t.name)})
                   for t in db.metadata.sorted_tables):
                raise RuntimeError('Schema incompleto. Execute migração explícita com backup antes de publicar.')

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config['DEBUG'])
