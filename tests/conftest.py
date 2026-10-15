"""
Configuração de fixtures para testes.
"""
import pytest
from utils import hash_senha

# Hash real compartilhado entre fixtures; evita recalcular em cada teste.
SENHA_TESTE = hash_senha("123456")
from app import create_app
from database import db
from models import Participante, Campeonato, Rodada, Jogo, Palpite, Resultado


@pytest.fixture
def app():
    """Cria uma aplicação Flask para testes."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def init_db(app):
    """Inicializa o banco de dados para testes."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cria um cliente de teste."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Cria um runner de teste CLI."""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Cria uma sessão de banco de dados para testes."""
    with app.app_context():
        yield db.session


@pytest.fixture
def participante_teste(db_session):
    """Cria um participante de teste."""
    participante = Participante(
        nome="Teste User",
        email="teste@example.com",
        senha=SENHA_TESTE,  # Senha: 123456
        admin=False
    )
    db_session.add(participante)
    db_session.commit()
    return participante


@pytest.fixture
def admin_teste(db_session):
    """Cria um administrador de teste."""
    admin = Participante(
        nome="Admin User",
        email="admin@example.com",
        senha=SENHA_TESTE,  # Senha: 123456
        admin=True
    )
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def campeonato_teste(db_session):
    """Cria um campeonato de teste."""
    campeonato = Campeonato(
        nome="Campeonato Teste",
        ano=2025
    )
    db_session.add(campeonato)
    db_session.commit()
    return campeonato


@pytest.fixture
def rodada_teste(db_session, campeonato_teste):
    """Cria uma rodada de teste."""
    rodada = Rodada(
        nome="Rodada 1",
        campeonato_id=campeonato_teste.id,
        aberta=True
    )
    db_session.add(rodada)
    db_session.commit()
    return rodada


@pytest.fixture
def jogo_teste(db_session, rodada_teste):
    """Cria um jogo de teste."""
    jogo = Jogo(
        time_casa="Time A",
        time_fora="Time B",
        rodada_id=rodada_teste.id,
        especial=False,
        encerrado=False
    )
    db_session.add(jogo)
    db_session.commit()
    return jogo


@pytest.fixture
def jogo_com_resultado(db_session, jogo_teste):
    """Cria um jogo com resultado de teste."""
    resultado = Resultado(
        jogo_id=jogo_teste.id,
        gols_casa_real=2,
        gols_fora_real=1,
        primeiro_gol_real="Jogador A"
    )
    db_session.add(resultado)
    db_session.commit()
    jogo_teste.encerrado = True
    db_session.commit()
    return jogo_teste
