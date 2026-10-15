"""
Testes para utilitários (utils.py).
"""
import pytest
from utils import (
    validar_email,
    validar_senha,
    validar_nome,
    hash_senha,
    verificar_senha,
)


class TestValidarEmail:
    """Testes de validação de email."""

    def test_email_valido(self):
        assert validar_email("teste@example.com") is True
        assert validar_email("user.name@domain.co.uk") is True
        assert validar_email("user+tag@example.org") is True

    def test_email_invalido(self):
        assert validar_email("") is False
        assert validar_email("invalido") is False
        assert validar_email("@example.com") is False
        assert validar_email("user@") is False
        assert validar_email("user @example.com") is False


class TestValidarSenha:
    """Testes de validação de senha."""

    def test_senha_valida(self):
        valido, msg = validar_senha("123456")
        assert valido is True
        assert msg == ""

    def test_senha_curta(self):
        valido, msg = validar_senha("12345")
        assert valido is False
        assert "pelo menos 6 caracteres" in msg

    def test_senha_vazia(self):
        valido, msg = validar_senha("")
        assert valido is False
        assert "pelo menos 6 caracteres" in msg


class TestValidarNome:
    """Testes de validação de nome."""

    def test_nome_valido(self):
        assert validar_nome("João Silva") is True
        assert validar_nome("Maria") is True
        assert validar_nome("AB") is True

    def test_nome_invalido(self):
        assert validar_nome("") is False
        assert validar_nome("   ") is False
        assert validar_nome("A") is False


class TestHashSenha:
    """Testes de hash de senha."""

    def test_hash_e_verificar(self):
        senha = "minha_senha_segura"
        hash_gerado = hash_senha(senha)

        assert hash_gerado != senha
        assert verificar_senha(senha, hash_gerado) is True
        assert verificar_senha("senha_errada", hash_gerado) is False
