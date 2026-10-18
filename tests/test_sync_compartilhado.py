"""Sincronização compartilhada: bolões da mesma competição/temporada usam uma única chamada à API."""
from datetime import datetime
from unittest.mock import patch

from database import db
from models import Campeonato, Jogo, Resultado, Rodada
from services.sync import campeonatos_da_competicao, sync_competicao, sync_jogos, sync_resultados
from tests.test_interface import entrar, gestao  # noqa: F401


def _item(id, estagio="REGULAR_SEASON", matchday=1, casa="Flamengo", fora="Palmeiras",
          finalizado=False, gols=(None, None), data=None):
    return {"external_id": str(id), "matchday": matchday, "estagio": estagio, "time_casa": casa,
            "time_fora": fora, "data": data, "finalizado": finalizado,
            "gols_casa_real": gols[0], "gols_fora_real": gols[1]}


def _campeonato(nome, codigo="BSA", ano=2026, rodada=True):
    c = Campeonato(nome=nome, ano=ano, codigo_api=codigo)
    db.session.add(c)
    db.session.flush()
    if rodada:
        db.session.add(Rodada(nome="Rodada 1", campeonato_id=c.id))
    db.session.commit()
    return c


def _jogo(campeonato, external_id="1", casa="Flamengo", fora="Palmeiras"):
    rodada = Rodada.query.filter_by(campeonato_id=campeonato.id, nome="Rodada 1").one()
    jogo = Jogo(time_casa=casa, time_fora=fora, rodada_id=rodada.id, external_fonte="football-data.org",
                external_id=external_id, data=datetime(2026, 5, 1, 16))
    db.session.add(jogo)
    db.session.commit()
    return jogo


def test_copa_nomeia_mata_mata_pela_fase(app):
    camp = _campeonato("Libertadores", codigo="CLI", rodada=False)
    itens = [_item(1, "QUALIFICATION_ROUND_1", 1), _item(2, "GROUP_STAGE", 1), _item(3, "GROUP_STAGE", 6),
             _item(4, "LAST_16", None), _item(5, "LAST_16", None), _item(6, "QUARTER_FINALS", None),
             _item(7, "SEMI_FINALS", None), _item(8, "FINAL", None)]
    with patch("services.sync.buscar_jogos_football_data", return_value=itens):
        sync_jogos("t", camp.id, "CLI", campeonato_completo=True)
    nomes = {r.nome: len(r.jogos) for r in Rodada.query.filter_by(campeonato_id=camp.id)}
    assert nomes == {"Rodada 0 · Fase preliminar": 1, "Rodada 1": 1, "Rodada 6": 1,
                     "Rodada 7 · Oitavas de final": 2, "Rodada 8 · Quartas de final": 1,
                     "Rodada 9 · Semifinal": 1, "Rodada 10 · Final": 1}


def test_mata_mata_sem_nome_de_rodada_usa_a_fase(app):
    camp = _campeonato("Libertadores", codigo="CLI", rodada=False)
    itens = [_item(1, "GROUP_STAGE", 6), _item(2, "LAST_16", None)]
    with patch("services.sync.buscar_jogos_football_data", return_value=itens):
        sync_jogos("t", camp.id, "CLI", rodada_api=None)
    nomes = {r.nome for r in Rodada.query.filter_by(campeonato_id=camp.id)}
    assert nomes == {"Rodada 6", "Rodada 7 · Oitavas de final"}


def test_dois_campeonatos_da_mesma_competicao_recebem_jogos_e_resultados(app):
    a, b = _campeonato("Bolão A", rodada=False), _campeonato("Bolão B", rodada=False)
    api = [_item(1, casa="CA Mineiro", fora="SC Corinthians Paulista"), _item(2, casa="Flamengo", fora="Fluminense")]
    with patch("services.sync.buscar_jogos_football_data", return_value=api) as busca:
        jogos_api = busca(token="t", competicao="BSA", temporada=2026)
        for camp in (a, b):
            r = sync_jogos("t", camp.id, "BSA", temporada=2026, campeonato_completo=True, jogos_api=jogos_api)
            assert r["criados"] == 2
    assert busca.call_count == 1
    for camp in (a, b):
        jogos = Jogo.query.join(Rodada).filter(Rodada.campeonato_id == camp.id).all()
        assert sorted((j.time_casa, j.time_fora) for j in jogos) == [
            ("Atlético-MG", "Corinthians"), ("Flamengo", "Fluminense")]

    # Uma nova sincronização não duplica nem move jogos entre os bolões.
    with patch("services.sync.buscar_jogos_football_data", return_value=api):
        assert sync_jogos("t", b.id, "BSA", campeonato_completo=True)["criados"] == 0
    assert Jogo.query.filter_by(external_id="1").count() == 2

    resultados = [{"external_id": "1", "gols_casa_real": 2, "gols_fora_real": 1}]
    with patch("services.sync.buscar_resultados_football_data", return_value=resultados) as busca_res:
        r = sync_resultados("t", "BSA", temporada=2026)
    assert busca_res.call_count == 1 and r["atualizados"] == 2
    for jogo in Jogo.query.filter_by(external_id="1"):
        res = Resultado.query.filter_by(jogo_id=jogo.id).one()
        assert jogo.encerrado and (res.gols_casa_real, res.gols_fora_real) == (2, 1)


def test_sync_competicao_chama_api_uma_vez_para_tres_campeonatos(app):
    campeonatos = [_campeonato(f"Bolão {i}") for i in range(3)]
    for camp in campeonatos:
        _jogo(camp)
    _jogo(_campeonato("Outro ano", ano=2025))
    _campeonato("Sem rodadas", rodada=False)
    nova_data = datetime(2026, 5, 2, 18, 30)
    api = [_item(1, finalizado=True, gols=(3, 0), data=nova_data)]
    with patch("services.sync.buscar_jogos_football_data", return_value=api) as busca:
        resultado = sync_competicao("t", "BSA", 2026)
    assert busca.call_count == 1
    assert sorted(resultado) == sorted(c.id for c in campeonatos)
    assert {c.id for c in campeonatos_da_competicao("bsa", 2026)} == {c.id for c in campeonatos}
    for camp in campeonatos:
        jogo = Jogo.query.join(Rodada).filter(Rodada.campeonato_id == camp.id).one()
        assert jogo.data == nova_data and jogo.encerrado
        assert Resultado.query.filter_by(jogo_id=jogo.id).one().gols_casa_real == 3
    outro = Jogo.query.join(Rodada).join(Campeonato).filter(Campeonato.ano == 2025).one()
    assert not outro.encerrado


def test_falha_num_campeonato_nao_impede_os_outros(app):
    from services import sync as modulo
    campeonatos = [_campeonato(f"Bolão {i}") for i in range(3)]
    for camp in campeonatos:
        _jogo(camp)
    original = modulo.sync_informacoes_jogos

    def instavel(token, campeonato_id, *args, **kwargs):
        if campeonato_id == campeonatos[0].id:
            raise RuntimeError("falha local")
        return original(token, campeonato_id, *args, **kwargs)

    api = [_item(1, finalizado=True, gols=(1, 1))]
    with patch("services.sync.buscar_jogos_football_data", return_value=api) as busca, \
            patch("services.sync.sync_informacoes_jogos", side_effect=instavel):
        resultado = sync_competicao("t", "BSA", 2026)
    assert busca.call_count == 1
    assert sorted(resultado) == sorted(c.id for c in campeonatos[1:])
    encerrados = {c.id: Jogo.query.join(Rodada).filter(Rodada.campeonato_id == c.id).one().encerrado
                  for c in campeonatos}
    assert encerrados == {campeonatos[0].id: False, campeonatos[1].id: True, campeonatos[2].id: True}


def test_worker_agrupa_por_competicao_e_temporada(app, monkeypatch):
    from services.sync_automatico import sincronizar_ciclo
    _campeonato("A"), _campeonato("B"), _campeonato("C", codigo="bsa")
    _campeonato("D", ano=2025), _campeonato("E", codigo="CLI")
    chamadas = []
    monkeypatch.setattr("services.sync_automatico.sync_competicao",
                        lambda token, codigo, ano: chamadas.append((codigo, ano)) or {})
    app.config["FOOTBALL_DATA_TOKEN"] = "teste"
    sincronizar_ciclo(app)
    assert chamadas == [("BSA", 2025), ("BSA", 2026), ("CLI", 2026)]


def test_sincronizacao_manual_de_informacoes_aplica_aos_campeonatos_irmaos(client, gestao):
    usuario, boloes = gestao
    usuario.admin_global = True
    for bolao in boloes:
        bolao.campeonato.codigo_api = "BSA"
        db.session.add(Rodada(nome="Rodada 1", campeonato=bolao.campeonato))
    db.session.commit()
    for bolao in boloes:
        _jogo(bolao.campeonato)
    entrar(client, usuario)
    client.post("/interface/selecionar", data={"bolao_id": boloes[0].id})
    api = [_item(1, finalizado=True, gols=(2, 2))]
    with patch("services.importador_jogos.buscar_jogos_football_data", return_value=api) as busca:
        r = client.post("/interface/api/campeonato/sincronizar", json={"acao": "informacoes", "token": "t"})
    assert r.status_code == 200, r.get_json()
    assert busca.call_count == 1
    assert r.get_json()["outrosCampeonatos"] == 2 and "2 outro(s) bolão(ões)" in r.get_json()["mensagem"]
    for bolao in boloes:
        jogo = Jogo.query.join(Rodada).filter(Rodada.campeonato_id == bolao.campeonato_id).one()
        assert Resultado.query.filter_by(jogo_id=jogo.id).one().gols_fora_real == 2


def test_sincronizacao_manual_de_outra_temporada_nao_aplica_aos_irmaos(client, gestao):
    usuario, boloes = gestao
    usuario.admin_global = True
    for bolao in boloes:
        bolao.campeonato.codigo_api = "BSA"
        db.session.add(Rodada(nome="Rodada 1", campeonato=bolao.campeonato))
    db.session.commit()
    entrar(client, usuario)
    client.post("/interface/selecionar", data={"bolao_id": boloes[0].id})
    with patch("services.importador_jogos.buscar_jogos_football_data", return_value=[]):
        r = client.post("/interface/api/campeonato/sincronizar",
                        json={"acao": "informacoes", "token": "t", "temporada": "2025"})
    assert r.status_code == 200 and r.get_json()["outrosCampeonatos"] == 0


def test_import_so_do_mata_mata_nao_fica_antes_dos_grupos(app):
    camp = _campeonato("Libertadores", codigo="CLI", rodada=False)
    with patch("services.sync.buscar_jogos_football_data", return_value=[_item(1, "LAST_16", None)]):
        sync_jogos("t", camp.id, "CLI", data_inicio="2026-08-01", data_fim="2026-08-31")
    assert {r.nome for r in Rodada.query.filter_by(campeonato_id=camp.id)} == {"Rodada 7 · Oitavas de final"}


def test_fase_sorteada_depois_nao_renumera_nem_duplica(app):
    camp = _campeonato("Libertadores", codigo="CLI", rodada=False)
    with patch("services.sync.buscar_jogos_football_data", return_value=[_item(1, "QUARTER_FINALS", None)]):
        sync_jogos("t", camp.id, "CLI", campeonato_completo=True)
    with patch("services.sync.buscar_jogos_football_data",
               return_value=[_item(2, "LAST_16", None), _item(1, "QUARTER_FINALS", None)]):
        sync_jogos("t", camp.id, "CLI", campeonato_completo=True)
    nomes = {r.nome: len(r.jogos) for r in Rodada.query.filter_by(campeonato_id=camp.id)}
    assert nomes == {"Rodada 7 · Oitavas de final": 1, "Rodada 8 · Quartas de final": 1}


def test_competicao_sem_formato_numera_pelas_rodadas_ja_salvas(app):
    camp = _campeonato("Copa X", codigo="XYZ", rodada=False)
    with patch("services.sync.buscar_jogos_football_data", return_value=[_item(1, "GROUP_STAGE", 3)]):
        sync_jogos("t", camp.id, "XYZ", campeonato_completo=True)
    with patch("services.sync.buscar_jogos_football_data", return_value=[_item(2, "FINAL", None)]):
        sync_jogos("t", camp.id, "XYZ", campeonato_completo=True)
    nomes = {r.nome for r in Rodada.query.filter_by(campeonato_id=camp.id)}
    final = next(n for n in nomes if n.endswith("· Final"))
    assert nomes == {"Rodada 3", final} and int(final.split()[1]) > 3


def test_codigo_em_minusculas_continua_sincronizado(app):
    from services.sync import campeonatos_da_competicao
    camp = _campeonato("Antigo", codigo="bsa")
    assert [c.id for c in campeonatos_da_competicao("BSA", camp.ano)] == [camp.id]
