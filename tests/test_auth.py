"""
Testes para rotas de autenticação.
"""
import pytest
from flask import session
from models import Participante
from database import db


class TestSemCadastroPublico:
    """Só responsáveis entram; não há cadastro nem recuperação pública de senha."""

    @pytest.mark.parametrize('rota', ['/cadastro', '/resetar-senha'])
    @pytest.mark.parametrize('metodo', ['get', 'post'])
    def test_rotas_removidas(self, client, init_db, rota, metodo):
        assert getattr(client, metodo)(rota).status_code == 404
        assert Participante.query.count() == 0


class TestLogin:
    """Testes para rota de login."""

    def test_login_get_abre_a_interface(self, client):
        """A tela de login é a da interface; /login só recebe o formulário."""
        response = client.get("/login")
        assert response.status_code == 302 and response.location.endswith("/interface/")
        assert client.get("/").location.endswith("/interface/")

    def test_interface_inclui_token_csrf(self, app, client):
        app.config["WTF_CSRF_ENABLED"] = True
        response = client.get("/interface/")
        assert response.status_code == 200
        assert b'name="csrf-token"' in response.data and b'"csrfToken"' in response.data

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


@pytest.mark.parametrize('rota', ['/b/1/ranking', '/admin/palpites', '/boloes', '/ranking', '/jogos/3'])
def test_enderecos_antigos_levam_a_interface(client, rota):
    resposta = client.get(rota)
    assert resposta.status_code == 302 and resposta.location.endswith('/interface/')
    assert client.post(rota).status_code == 404


def test_erro_404_comum_e_json_na_api(client):
    assert client.get('/nao-existe').status_code == 404
    resposta = client.get('/interface/api/nao-existe')
    assert resposta.status_code == 404 and 'erro' in resposta.get_json()
