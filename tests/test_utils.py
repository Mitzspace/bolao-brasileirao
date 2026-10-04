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
    validar_arquivo_upload,
    normalizar_texto,
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


class TestValidarArquivoUpload:
    """Testes de validação de arquivo upload."""

    def test_arquivo_valido(self):
        valido, msg = validar_arquivo_upload("planilha.xlsx", ["xlsx", "xls"])
        assert valido is True
        assert msg == ""

    def test_arquivo_sem_extensao(self):
        valido, msg = validar_arquivo_upload("arquivo", ["xlsx", "xls"])
        assert valido is False
        assert "sem extensão" in msg

    def test_arquivo_extensao_invalida(self):
        valido, msg = validar_arquivo_upload("documento.pdf", ["xlsx", "xls"])
        assert valido is False
        assert "Extensão não permitida" in msg

    def test_arquivo_vazio(self):
        valido, msg = validar_arquivo_upload("", ["xlsx", "xls"])
        assert valido is False
        assert "Nenhum arquivo" in msg


class TestNormalizarTexto:
    """Testes de normalização de texto."""

    def test_normalizar_valido(self):
        assert normalizar_texto("  texto  ") == "texto"
        assert normalizar_texto("  João Silva  ") == "João Silva"

    def test_normalizar_vazio(self):
        assert normalizar_texto("") == ""
        assert normalizar_texto("   ") == ""
        assert normalizar_texto(None) == ""
