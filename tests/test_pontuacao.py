"""
Testes para o sistema de pontuação.
"""
import pytest
from types import SimpleNamespace

from services.pontuacao import calcular_pontuacao, normalizar_nome_jogador
from models import Palpite, Resultado


def calcular_pontos(palpite, resultado, especial=False):
    """Atalho dos testes: jogo comum ou clássico com o primeiro gol do resultado."""
    jogo = SimpleNamespace(classico=especial, primeiro_marcador=resultado.primeiro_gol_real)
    return calcular_pontuacao(palpite, jogo, resultado).total


class TestNormalizarNomeJogador:
    """Testes de normalização de nomes de jogadores."""

    def test_nome_com_acentos(self):
        assert normalizar_nome_jogador("João Silva") == "joao silva"
        assert normalizar_nome_jogador("José Éderson") == "jose ederson"

    def test_nome_com_maiusculas(self):
        assert normalizar_nome_jogador("JOÃO SILVA") == "joao silva"
        assert normalizar_nome_jogador("Teste TESTE") == "teste teste"

    def test_nome_com_espacos_extras(self):
        assert normalizar_nome_jogador("  João  Silva  ") == "joao silva"

    def test_nome_vazio(self):
        assert normalizar_nome_jogador("") == ""
        assert normalizar_nome_jogador(None) == ""


class TestCalcularPontos:
    """Testes de cálculo de pontos."""

    def test_placar_exato_jogo_normal(self):
        palpite = Palpite(gols_casa=2, gols_fora=1)
        resultado = Resultado(gols_casa_real=2, gols_fora_real=1)

        pontos = calcular_pontos(palpite, resultado, especial=False)
        assert pontos == 3

    def test_placar_exato_jogo_especial(self):
        palpite = Palpite(gols_casa=2, gols_fora=1)
        resultado = Resultado(gols_casa_real=2, gols_fora_real=1)

        pontos = calcular_pontos(palpite, resultado, especial=True)
        assert pontos == 5

    def test_acertou_vencedor_jogo_normal(self):
        palpite = Palpite(gols_casa=2, gols_fora=0)
        resultado = Resultado(gols_casa_real=3, gols_fora_real=1)

        pontos = calcular_pontos(palpite, resultado, especial=False)
        assert pontos == 1

    def test_acertou_vencedor_jogo_especial(self):
        palpite = Palpite(gols_casa=2, gols_fora=0)
        resultado = Resultado(gols_casa_real=3, gols_fora_real=1)

        pontos = calcular_pontos(palpite, resultado, especial=True)
        assert pontos == 3

    def test_errou_vencedor(self):
        palpite = Palpite(gols_casa=2, gols_fora=0)
        resultado = Resultado(gols_casa_real=0, gols_fora_real=2)

        pontos = calcular_pontos(palpite, resultado, especial=False)
        assert pontos == 0

    def test_empate_acertado(self):
        palpite = Palpite(gols_casa=1, gols_fora=1)
        resultado = Resultado(gols_casa_real=2, gols_fora_real=2)

        pontos = calcular_pontos(palpite, resultado, especial=False)
        assert pontos == 1

    def test_empate_errado(self):
        palpite = Palpite(gols_casa=1, gols_fora=1)
        resultado = Resultado(gols_casa_real=2, gols_fora_real=1)

        pontos = calcular_pontos(palpite, resultado, especial=False)
        assert pontos == 0

    def test_bonus_primeiro_gol_especial(self):
        palpite = Palpite(gols_casa=2, gols_fora=1, primeiro_gol="João Silva")
        resultado = Resultado(gols_casa_real=2, gols_fora_real=1, primeiro_gol_real="João Silva")

        pontos = calcular_pontos(palpite, resultado, especial=True)
        assert pontos == 7  # 5 placar exato + 2 bônus

    def test_bonus_primeiro_gol_normal(self):
        palpite = Palpite(gols_casa=2, gols_fora=1, primeiro_gol="João Silva")
        resultado = Resultado(gols_casa_real=2, gols_fora_real=1, primeiro_gol_real="João Silva")

        pontos = calcular_pontos(palpite, resultado, especial=False)
        assert pontos == 5  # placar comum + bônus, conforme regra confirmada

    def test_bonus_primeiro_gol_normalizado(self):
        palpite = Palpite(gols_casa=2, gols_fora=1, primeiro_gol="João Silva")
        resultado = Resultado(gols_casa_real=2, gols_fora_real=1, primeiro_gol_real="joão silva")

        pontos = calcular_pontos(palpite, resultado, especial=True)
        assert pontos == 7  # Bônus deve funcionar mesmo com normalização

    def test_bonus_primeiro_gol_errado(self):
        palpite = Palpite(gols_casa=2, gols_fora=1, primeiro_gol="João Silva")
        resultado = Resultado(gols_casa_real=2, gols_fora_real=1, primeiro_gol_real="Maria Santos")

        pontos = calcular_pontos(palpite, resultado, especial=True)
        assert pontos == 5  # 5 placar exato, sem bônus

    def test_bonus_sem_primeiro_gol_real(self):
        palpite = Palpite(gols_casa=2, gols_fora=1, primeiro_gol="João Silva")
        resultado = Resultado(gols_casa_real=2, gols_fora_real=1, primeiro_gol_real=None)

        pontos = calcular_pontos(palpite, resultado, especial=True)
        assert pontos == 5  # 5 placar exato, sem bônus pois não tem resultado real
