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

    # Compressão gzip e cache do navegador para os arquivos da interface (docs/DESEMPENHO.md).
    from services.http_desempenho import registrar as registrar_desempenho
    registrar_desempenho(app)

    # Inicializa extensões
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

    @app.get('/favicon.ico')
    @limiter.exempt
    def favicon():
        # Navegadores e favoritos pedem /favicon.ico direto na raiz.
        from flask import send_from_directory
        return send_from_directory(app.static_folder, 'icones/favicon.ico', mimetype='image/x-icon',
                                   max_age=604800)

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

    from routes.auth import auth
    from routes.interface import interface
    from routes.api import api
    from routes.publico import publico

    app.register_blueprint(auth)
    app.register_blueprint(interface)
    app.register_blueprint(api)
    # Área pública somente leitura (docs/LINK_PUBLICO.md); importa o cache que se limpa a cada gravação.
    app.register_blueprint(publico)

    from services.contexto_bolao import carregar_contexto, gravar_cookie_ultimo_bolao
    app.before_request(carregar_contexto)
    app.after_request(gravar_cookie_ultimo_bolao)

    @app.get('/')
    def inicio():
        # A nova interface é a entrada do sistema.
        from flask import redirect, url_for
        return redirect(url_for('interface.index'))

    # Páginas de erro simples (a API da interface responde em JSON pelos próprios handlers).
    def pagina_erro(codigo, titulo, texto):
        from flask import request
        from routes.api import api as api_bp, erro
        if request.path.startswith(api_bp.url_prefix + '/'):
            return erro(codigo)
        return render_template('erro.html', codigo=codigo, titulo=titulo, texto=texto), codigo

    @app.errorhandler(403)
    def acesso_negado(e):
        return pagina_erro(403, 'Acesso não permitido', 'Esta área é só para responsáveis pelo bolão.')

    # Endereços das telas antigas (favoritos, links salvos) levam à interface nova.
    ENDERECOS_ANTIGOS = ('/b/', '/admin', '/boloes', '/ranking', '/jogos', '/rodada', '/meus-palpites', '/tabela')

    @app.errorhandler(404)
    def nao_encontrado(e):
        from flask import redirect, request, url_for
        if request.method == 'GET' and request.path.startswith(ENDERECOS_ANTIGOS):
            return redirect(url_for('interface.index'))
        return pagina_erro(404, 'Página não encontrada', 'O endereço não existe ou mudou.')

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return pagina_erro(429, 'Muitas tentativas', 'Aguarde alguns minutos e tente novamente.')

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return pagina_erro(403, 'Sessão expirada', 'Recarregue a página e tente novamente.')

    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if db.engine.dialect.name == 'postgresql' and inspector.get_table_names():
            tabelas_pg = set(inspector.get_table_names())
            faltantes = []
            for tabela in db.metadata.sorted_tables:
                presentes = ({c['name'] for c in inspector.get_columns(tabela.name)}
                             if tabela.name in tabelas_pg else set())
                faltantes.extend(f'{tabela.name}.{coluna}' for coluna in tabela.columns.keys()
                                 if coluna not in presentes)
            if faltantes:
                raise RuntimeError(
                    'Schema PostgreSQL incompleto. Faltam: ' + ', '.join(faltantes) +
                    '. Aplique as migrações SQL pendentes em migrations/sql após backup; '
                    'não execute os scripts legados SQLite neste banco.')
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
                raise RuntimeError("Banco anterior à Fase 1. Revise docs/MIGRACAO_FASE1.md e execute a migração explícita com backup. O app não migra o banco automaticamente.")
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
                raise RuntimeError("Migração de participação pendente. Siga docs/MIGRACAO_PARTICIPACAO.md; o banco não é migrado automaticamente.")
            if 'email' not in {c['name'] for c in inspector.get_columns('participacao')}:
                raise RuntimeError('Migração pendente: execute python -m migrations.contato_participante CAMINHO_DO_BANCO.')
            if 'situacao' not in {c['name'] for c in inspector.get_columns('palpite')}:
                raise RuntimeError('Migração pendente: execute python -m migrations.situacao_palpite CAMINHO_DO_BANCO. Consulte docs/AJUSTES_PALPITES_SYNC.md.')
            if 'grupo_id' not in {c['name'] for c in inspector.get_columns('bolao')}:
                raise RuntimeError('Migração pendente: execute python -m migrations.grupo_bolao CAMINHO_DO_BANCO. Consulte docs/MULTIPLOS_CAMPEONATOS.md.')
            if 'pontos_primeiro_gol' not in {c['name'] for c in inspector.get_columns('bolao')}:
                raise RuntimeError('Migração pendente: execute python -m migrations.regras_bolao CAMINHO_DO_BANCO. Consulte docs/REGRAS_POR_BOLAO.md.')
            if 'ordem' not in {c['name'] for c in inspector.get_columns('jogo')}:
                raise RuntimeError('Migração pendente: execute python -m migrations.ordem_jogo CAMINHO_DO_BANCO. Consulte docs/DESEMPENHO.md.')
            if 'codigo_publico' not in {c['name'] for c in inspector.get_columns('bolao')}:
                raise RuntimeError('Migração pendente: execute python -m migrations.link_publico CAMINHO_DO_BANCO. Consulte docs/LINK_PUBLICO.md.')
            if ('eliminacao_participantes' not in {c['name'] for c in inspector.get_columns('bolao')}
                    or 'corte_eliminacao' not in inspector.get_table_names()):
                raise RuntimeError('Migração pendente: execute python -m migrations.eliminacao CAMINHO_DO_BANCO. Consulte docs/COPAS_ELIMINACAO.md.')
            if ('pode_penaltis' not in {c['name'] for c in inspector.get_columns('jogo')}
                    or 'fonte_api' not in {c['name'] for c in inspector.get_columns('campeonato')}):
                raise RuntimeError('Migração pendente: execute python -m migrations.penaltis CAMINHO_DO_BANCO. Consulte docs/COPAS_ELIMINACAO.md.')
            codigo_api = next(c for c in inspector.get_columns('campeonato') if c['name'] == 'codigo_api')
            tamanho = getattr(codigo_api['type'], 'length', None)
            if tamanho is not None and tamanho < 40 and not db.engine.dialect.name.startswith('sqlite'):
                raise RuntimeError(
                    'Migração pendente: aplique migrations/sql/012_codigo_api_espn.sql '
                    '(ou python -m migrations.codigo_api_espn no SQLite). Consulte docs/COPAS_ELIMINACAO.md.')
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
