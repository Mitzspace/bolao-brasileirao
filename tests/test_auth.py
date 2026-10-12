"""
Testes para rotas de autenticação.
"""
import pytest
from flask import session
from models import Participante
from database import db


class TestCadastro:
    """Testes para rota de cadastro."""

    def test_cadastro_get(self, client):
        """Testa acesso à página de cadastro."""
        response = client.get("/cadastro")
        assert response.status_code == 200
        assert b"Criar conta" in response.data

    def test_cadastro_sucesso(self, client, init_db):
        """Testa cadastro com dados válidos."""
        response = client.post("/cadastro", data={
            "nome": "Novo Usuario",
            "email": "novo@example.com",
            "senha": "123456",
        }, follow_redirects=True)

        assert response.status_code == 200

        # Verifica se usuário foi criado
        participante = Participante.query.filter_by(email="novo@example.com").first()
        assert participante is not None
        assert participante.nome == "Novo Usuario"
        assert participante.admin is False

    def test_cadastro_email_duplicado(self, client, participante_teste):
        """Testa cadastro com email já existente."""
        response = client.post("/cadastro", data={
            "nome": "Outro Usuario",
            "email": participante_teste.email,
            "senha": "123456",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"ja esta cadastrado" in response.data

    def test_cadastro_nome_invalido(self, client):
        """Testa cadastro com nome muito curto."""
        response = client.post("/cadastro", data={
            "nome": "A",
            "email": "teste@example.com",
            "senha": "123456",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Nome inv" in response.data

    def test_cadastro_email_invalido(self, client):
        """Testa cadastro com email inválido."""
        response = client.post("/cadastro", data={
            "nome": "Teste",
            "email": "email_invalido",
            "senha": "123456",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Email inv" in response.data

    def test_cadastro_senha_curta(self, client):
        """Testa cadastro com senha muito curta."""
        response = client.post("/cadastro", data={
            "nome": "Teste",
            "email": "teste@example.com",
            "senha": "123",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"senha deve ter" in response.data


class TestLogin:
    """Testes para rota de login."""

    def test_login_get(self, client):
        """Testa acesso à página de login."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Entrar" in response.data

    def test_login_get_includes_csrf_token_when_enabled(self, app, client):
        """Testa que o formulário renderiza o token CSRF quando a proteção está ativa."""
        app.config["WTF_CSRF_ENABLED"] = True

        response = client.get("/login")

        assert response.status_code == 200
        assert b'name="csrf_token"' in response.data

    def test_login_sucesso(self, client, participante_teste):
        """Testa login com credenciais válidas."""
        # Primeiro precisamos atualizar a senha para um hash válido
        from utils import hash_senha
        participante_teste.senha = hash_senha("123456")
        db.session.commit()

        response = client.post("/login", data={
            "email": participante_teste.email,
            "senha": "123456",
        }, follow_redirects=True)

        assert response.status_code == 200

    def test_login_email_inexistente(self, client):
        """Testa login com email não cadastrado."""
        response = client.post("/login", data={
            "email": "inexistente@example.com",
            "senha": "123456",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Email ou senha invalidos" in response.data

    def test_login_senha_errada(self, client, participante_teste):
        """Testa login com senha incorreta."""
        from utils import hash_senha
        participante_teste.senha = hash_senha("123456")
        db.session.commit()

        response = client.post("/login", data={
            "email": participante_teste.email,
            "senha": "senha_errada",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Email ou senha invalidos" in response.data

    def test_login_email_invalido(self, client):
        """Testa login com email inválido."""
        response = client.post("/login", data={
            "email": "email_invalido",
            "senha": "123456",
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Email inv" in response.data


class TestLogout:
    """Testes para rota de logout."""

    def test_logout(self, client, participante_teste):
        """Testa logout."""
        from utils import hash_senha
        from flask_login import login_user

        participante_teste.senha = hash_senha("123456")
        db.session.commit()

                # Faz login
        with client.session_transaction() as sess:
            sess['_user_id'] = str(participante_teste.id)

        response = client.get("/logout", follow_redirects=True)
        assert response.status_code == 200


class TestResetarSenha:
    def test_orientacao_sem_formulario_de_reset(self, client):
        response = client.get('/resetar-senha')
        assert response.status_code == 200
        assert b'administrador do sistema' in response.data
        assert b'<form' not in response.data

    @pytest.mark.parametrize('email', ['teste@example.com', 'naoexiste@example.com', 'invalido', ''])
    def test_reset_publico_nunca_altera_senha(self, client, participante_teste, email):
        anterior = participante_teste.senha
        response = client.post('/resetar-senha', data={'email': email}, follow_redirects=True)
        db.session.refresh(participante_teste)
        assert response.status_code == 200
        assert participante_teste.senha == anterior
        assert b'administrador do sistema' in response.data
