"""Importar a partir de uma fase (ex.: Copa do Brasil só dos 16 avos em diante)."""
import pytest

from services.competicoes import filtrar_a_partir_da_fase, ordem_fase, validar_fase_inicial

LIGA = "bra.copa_do_brazil"


def _jogos():
    return [{"external_id": str(i), "estagio": e} for i, e in enumerate(
        ["ROUND_1", "ROUND_2", "ROUND_3", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL", "OUTRA"])]


def _estagios(itens):
    return [i["estagio"] for i in itens]


def test_sem_fase_inicial_importa_tudo():
    assert filtrar_a_partir_da_fase(_jogos(), None, LIGA) == _jogos()


def _fase(estagio, times):
    """Jogos de ida e volta de uma fase numerada com `times` times."""
    return [{"external_id": f"{estagio}-{n}-{perna}", "estagio": estagio,
             "time_casa": f"{estagio} T{n}", "time_fora": f"{estagio} T{n + 1}"}
            for n in range(0, times, 2) for perna in (1, 2)]


@pytest.mark.parametrize("fases, dezesseis_avos", [
    ([("ROUND_1", 80), ("ROUND_2", 64), ("ROUND_3", 32)], "ROUND_3"),               # até 2025
    ([("ROUND_1", 28), ("ROUND_2", 88), ("ROUND_3", 48), ("ROUND_4", 24), ("ROUND_5", 32)], "ROUND_5"),  # 2026
])
def test_copa_do_brasil_16_avos_e_a_fase_numerada_com_32_times(fases, dezesseis_avos):
    itens = [j for estagio, times in fases for j in _fase(estagio, times)] + [{"estagio": "LAST_16"}]
    assert sorted(set(_estagios(filtrar_a_partir_da_fase(itens, "LAST_32", LIGA)))) == [
        "LAST_16", dezesseis_avos]


def test_copa_do_brasil_sem_fase_de_32_times_comeca_nas_oitavas():
    itens = _fase("ROUND_3", 48) + [{"estagio": "LAST_16"}]
    assert _estagios(filtrar_a_partir_da_fase(itens, "LAST_32", LIGA)) == ["LAST_16"]


def test_modelo_copa_do_brasil_comeca_nas_oitavas():
    from services.competicoes import MODELOS_COMPETICAO
    assert MODELOS_COMPETICAO["copadobrasil"]["fase_inicial"] == "LAST_16"


def test_16_avos_com_estagio_proprio_em_outra_liga():
    itens = [{"estagio": "GROUP_STAGE"}, {"estagio": "LAST_32"}, {"estagio": "LAST_16"}]
    assert _estagios(filtrar_a_partir_da_fase(itens, "LAST_32", "conmebol.libertadores")) == ["LAST_32", "LAST_16"]


def test_oitavas_em_diante():
    assert _estagios(filtrar_a_partir_da_fase(_jogos(), "LAST_16", LIGA)) == [
        "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL", "OUTRA"]


def test_ordem_das_fases():
    assert ordem_fase("ROUND_1") < ordem_fase("GROUP_STAGE") < ordem_fase("LAST_32") < ordem_fase("FINAL")
    assert ordem_fase("OUTRA") is None


def test_validar_fase_inicial():
    assert validar_fase_inicial(None) is None and validar_fase_inicial("") is None
    assert validar_fase_inicial("LAST_32") == "LAST_32"
    with pytest.raises(ValueError):
        validar_fase_inicial("LAST_999")
    with pytest.raises(ValueError):
        validar_fase_inicial(["LAST_32"])
