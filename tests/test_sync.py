"""
Testes para sincronizacao de jogos e propriedades do modelo Jogo.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from models import Jogo
from services.sync import sync_informacoes_jogos


def _jogo_api(external_id, time_casa, time_fora, data=None, finalizado=False,
              gols_casa_real=None, gols_fora_real=None, matchday=1):
    """Factory para itens retornados pela API."""
    return {
        "external_id": str(external_id),
        "matchday": matchday,
        "time_casa": time_casa,
        "time_fora": time_fora,
        "data": data,
        "finalizado": finalizado,
        "gols_casa_real": gols_casa_real,
        "gols_fora_real": gols_fora_real,
    }


class TestDataFormatada:
    """Testes para a propriedade Jogo.data_formatada."""

    def test_data_formatada_com_data(self):
        jogo = Jogo(time_casa="A", time_fora="B", data=datetime(2025, 5, 15, 20, 30))
        assert jogo.data_formatada == "15/05/2025 a as 20:30"

    def test_data_formatada_sem_data_encerrado(self):
        jogo = Jogo(time_casa="A", time_fora="B", data=None, encerrado=True)
        assert jogo.data_formatada == "Partida finalizada"

    def test_data_formatada_sem_data_aberto(self):
        jogo = Jogo(time_casa="A", time_fora="B", data=None, encerrado=False)
        assert jogo.data_formatada == "Horario a definir"

    def test_data_formatada_data_prioriza_sobre_encerrado(self):
        jogo = Jogo(time_casa="A", time_fora="B",
                    data=datetime(2025, 5, 15, 20, 30), encerrado=True)
        assert jogo.data_formatada == "15/05/2025 a as 20:30"
        assert jogo.data_formatada == "15/05/2025 a as 20:30"


class TestJogoBloqueado:
    """Testes para o metodo Jogo.bloqueado()."""

    def test_bloqueado_encerrado_manualmente(self):
        jogo = Jogo(time_casa="A", time_fora="B", encerrado=True)
        assert jogo.bloqueado() is True

    def test_bloqueado_data_no_passado(self):
        jogo = Jogo(time_casa="A", time_fora="B",
                    encerrado=False, data=datetime(2020, 1, 1, 10, 0))
        assert jogo.bloqueado() is True

    def test_nao_bloqueado_data_no_futuro(self):
        jogo = Jogo(time_casa="A", time_fora="B",
                    encerrado=False, data=datetime.now() + timedelta(days=30))
        assert jogo.bloqueado() is False

        def test_nao_bloqueado_sem_data(self):
        jogo = Jogo(time_casa="A", time_fora="B", encerrado=False, data=None)
        assert jogo.bloqueado() is False


class TestSyncInformacoesJogos:
    """Testes para sync_informacoes_jogos (atualiza apenas info, nao cria jogos)."""

    @patch("services.sync.buscar_jogos_football_data")
    def test_sync_atualiza_data_hora_sem_criar_jogos(
        self, mock_buscar, app, db_session, jogo_teste, campeonato_teste
    ):
        nova_data = datetime(2025, 6, 20, 16, 0)
        mock_buscar.return_value = [
            _jogo_api("1", "Time A", "Time B", data=nova_data)
        ]

        jogo_teste.external_fonte = "football-data.org"
        jogo_teste.external_id = "1"
        jogo_teste.data = None
        db_session.commit()

        total_before = Jogo.query.count()
        res = sync_informacoes_jogos(
            token="fake-token",
            campeonato_id=campeonato_teste.id,
            competicao="BSA",
        )

        jogo = Jogo.query.get(jogo_teste.id)
        assert jogo.data == nova_data
        assert Jogo.query.count() == total_before
        assert res["atualizados"] == 1
        assert res["horarios_atualizados"] == 1
        assert res["ignorados"] == 0

    @patch("services.sync.buscar_jogos_football_data")
    def test_sync_salva_resultado_jogo_finalizado(
        self, mock_buscar, app, db_session, jogo_teste, campeonato_teste
    ):
        mock_buscar.return_value = [
            _jogo_api("1", "Time A", "Time B", data=None, finalizado=True,
                      gols_casa_real=2, gols_fora_real=1)
        ]

        jogo_teste.external_fonte = "football-data.org"
        jogo_teste.external_id = "1"
        db_session.commit()

        res = sync_informacoes_jogos(
            token="fake-token",
            campeonato_id=campeonato_teste.id,
            competicao="BSA",
        )

        jogo = Jogo.query.get(jogo_teste.id)
        assert jogo.encerrado is True
        assert jogo.resultado is not None
        assert jogo.resultado.gols_casa_real == 2
        assert jogo.resultado.gols_fora_real == 1
        assert res["resultados_salvos"] == 1