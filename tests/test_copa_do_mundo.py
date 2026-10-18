from config_selecoes import SELECOES, logo_selecao
from services.competicoes import MODELOS_COMPETICAO, nomeador_rodadas, tema_do_campeonato
from services.escudos import escudo_time
from services.importador_espn import converter_eventos
from services.sync import _normalizar_texto


def _evento(eid, slug, casa, fora, data="2026-06-11T19:00Z"):
    def lado(onde, nome):
        return {"homeAway": onde, "score": "0", "team": {"displayName": nome}}
    return {"id": eid, "season": {"slug": slug}, "date": data, "competitions": [{
        "date": data, "competitors": [lado("home", casa), lado("away", fora)],
        "status": {"type": {"name": "STATUS_SCHEDULED", "state": "pre", "completed": False}}}]}


def test_modelo_copa_do_mundo_usa_espn_e_tema():
    modelo = MODELOS_COMPETICAO["copadomundo"]
    assert modelo["codigo_api"] == "fifa.world" and modelo["fonte_api"] == "espn" and modelo["eliminacao"]
    assert tema_do_campeonato("fifa.world") == "copa-do-mundo"
    assert tema_do_campeonato("FIFA.World") == "copa-do-mundo"
    assert tema_do_campeonato("conmebol.libertadores") == "libertadores"
    assert tema_do_campeonato("bra.copa_do_brazil") == "copa-do-brasil"
    assert tema_do_campeonato("BSA") == "brasileirao"
    assert tema_do_campeonato("PL") is None and tema_do_campeonato(None) is None


def test_fases_da_copa_viram_rodadas_em_ordem():
    eventos = [
        _evento("1", "group-stage", "Brasil", "Marrocos", "2026-06-13T19:00Z"),
        _evento("2", "group-stage", "Haiti", "Escócia", "2026-06-13T22:00Z"),
        _evento("3", "round-of-32", "Brasil", "Japão", "2026-06-29T19:00Z"),
        _evento("4", "round-of-16", "Brasil", "França", "2026-07-04T19:00Z"),
        _evento("5", "quarterfinals", "Brasil", "Argentina", "2026-07-09T19:00Z"),
        _evento("6", "semifinals", "Brasil", "Espanha", "2026-07-14T19:00Z"),
        _evento("7", "3rd-place-match", "Brasil", "Alemanha", "2026-07-18T19:00Z"),
        _evento("8", "final", "Brasil", "Inglaterra", "2026-07-19T19:00Z"),
    ]
    jogos = converter_eventos({"events": eventos})
    assert [j["estagio"] for j in jogos] == ["GROUP_STAGE", "GROUP_STAGE", "LAST_32", "LAST_16",
                                              "QUARTER_FINALS", "SEMI_FINALS", "THIRD_PLACE", "FINAL"]
    nome = nomeador_rodadas("espn", jogos, "fifa.world")
    assert [nome(j) for j in jogos[2:]] == [
        "Rodada 4 · 16 avos de final", "Rodada 5 · Oitavas de final", "Rodada 6 · Quartas de final",
        "Rodada 7 · Semifinal", "Rodada 8 · Disputa de 3º lugar", "Rodada 9 · Final"]
    assert nome(jogos[0]).startswith("Rodada 1 · ")


def test_toda_selecao_tem_logo_e_sigla(app):
    assert len(SELECOES) >= 48
    with app.test_request_context():
        for chave in SELECOES:
            escudo = escudo_time(chave)
            assert escudo["fontes"] == [logo_selecao(chave)], chave
            assert len(escudo["sigla"]) == 3, chave


def test_logo_de_selecoes_com_acento_e_curacao(app):
    with app.test_request_context():
        assert escudo_time("Brasil")["fontes"] == ["https://a.espncdn.com/i/teamlogos/countries/500/bra.png"]
        assert escudo_time("Coreia do Sul")["fontes"][0].endswith("/kor.png")
        assert escudo_time("Curaçao")["fontes"][0].endswith("/soccer/500/11678.png")
        assert escudo_time("Costa do Marfim")["sigla"] == "CDM"
        assert escudo_time("Time Qualquer")["fontes"] == []


def test_chaves_das_selecoes_estao_normalizadas():
    assert all(chave == _normalizar_texto(chave) for chave in SELECOES)
