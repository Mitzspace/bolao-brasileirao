"""Primeiro marcador pela ESPN: leitura dos lances, sincronização e conferência dos bônus antigos."""
from datetime import datetime, timedelta
from unittest.mock import patch

from database import db
from models import Bolao, BonusRodada, Campeonato, Jogo, Palpite, Participacao, Participante, Resultado, Rodada
from services import primeiro_gol
from services.conferencia_primeiro_gol import aplicar, conferir
from services.importador_espn import converter_eventos, primeiro_gol_dos_detalhes
from services.ranking import calcular_ranking
from services.sync import sync_resultados


def lance(texto, nome=None, *, gol=True, contra=False, shootout=False):
    item = {"type": {"text": texto}, "scoringPlay": gol, "ownGoal": contra,
            "athletesInvolved": [{"displayName": nome}] if nome else []}
    if shootout:
        item["shootout"] = True
    return item


def evento(eid, casa, fora, placar, data, detalhes=None):
    comp = {"date": data, "status": {"type": {"name": "STATUS_FULL_TIME", "completed": True, "state": "post"}},
            "competitors": [{"homeAway": "home", "score": str(placar[0]), "team": {"displayName": casa}},
                            {"homeAway": "away", "score": str(placar[1]), "team": {"displayName": fora}}]}
    if detalhes is not None:
        comp["details"] = detalhes
    return {"id": eid, "date": data, "season": {"slug": "regular-season"}, "competitions": [comp]}


def test_primeiro_gol_conta_gol_contra_e_ignora_cartoes_e_penaltis():
    assert primeiro_gol_dos_detalhes({"details": [
        lance("Yellow Card", "Fulano", gol=False),
        lance("Own Goal", "Bruno Henrique", contra=True),
        lance("Goal", "Pedro"),
    ]}) == "Bruno Henrique"
    assert primeiro_gol_dos_detalhes({"details": [lance("Penalty - Scored", "X", shootout=True)]}) is None
    # Primeiro gol sem autor: não arrisca o segundo.
    assert primeiro_gol_dos_detalhes({"details": [lance("Goal"), lance("Goal", "Pedro")]}) is None
    assert primeiro_gol_dos_detalhes({}) is None


def test_conversor_espn_traz_o_marcador_so_de_jogo_encerrado():
    dados = {"events": [evento("1", "Corinthians", "Fluminense", (1, 3), "2026-09-20T19:00Z",
                               [lance("Goal", "Hulk"), lance("Goal", "Gustavo Henrique")])]}
    assert converter_eventos(dados)[0]["primeiro_marcador"] == "Hulk"


def _campeonato(fonte="espn", codigo="bra.1"):
    camp = Campeonato(nome="Brasileirão", codigo_api=codigo, fonte_api=fonte, ano=2026)
    rodada = Rodada(nome="Rodada 1", campeonato=camp)
    db.session.add_all([camp, rodada])
    db.session.flush()
    return camp, rodada


def _jogo(rodada, casa, fora, *, classico=True, marcador=None, placar=None, data=None, eid=None):
    jogo = Jogo(time_casa=casa, time_fora=fora, rodada=rodada, classico=classico, primeiro_marcador=marcador,
                data=data, external_fonte="espn" if eid else None, external_id=eid)
    db.session.add(jogo)
    db.session.flush()
    if placar:
        db.session.add(Resultado(jogo=jogo, gols_casa_real=placar[0], gols_fora_real=placar[1]))
    return jogo


def test_sincronizacao_espn_preenche_so_classico_sem_marcador_digitado(app):
    _, rodada = _campeonato()
    vazio = _jogo(rodada, "Corinthians", "Palmeiras", eid="1")
    digitado = _jogo(rodada, "Flamengo", "Vasco", marcador="Pedro", eid="2")
    comum = _jogo(rodada, "Bahia", "Vitória", classico=False, eid="3")
    sem_gol = _jogo(rodada, "Grêmio", "Internacional", eid="4")
    db.session.commit()
    itens = [dict(external_id="1", gols_casa_real=1, gols_fora_real=0, primeiro_marcador="Yuri Alberto"),
             dict(external_id="2", gols_casa_real=2, gols_fora_real=0, primeiro_marcador="Bruno Henrique"),
             dict(external_id="3", gols_casa_real=1, gols_fora_real=1, primeiro_marcador="Everaldo"),
             dict(external_id="4", gols_casa_real=0, gols_fora_real=0, primeiro_marcador=None)]
    with patch("services.importador_espn.buscar_resultados_espn", return_value=itens):
        sync_resultados(None, "bra.1", fonte_api="espn", temporada=2026)
    assert vazio.primeiro_marcador == "Yuri Alberto" and vazio.resultado.primeiro_gol_real == "Yuri Alberto"
    assert digitado.primeiro_marcador == "Pedro"
    assert comum.primeiro_marcador is None and sem_gol.primeiro_marcador is None


def test_campeonato_da_football_data_busca_o_dia_na_espn_uma_vez(app):
    camp, rodada = _campeonato("football-data", "BSA")
    ontem = datetime.now() - timedelta(days=1)
    jogo = _jogo(rodada, "Corinthians", "Fluminense", placar=(1, 3), data=ontem)
    db.session.commit()
    dados = {"events": [evento("9", "Corinthians", "Fluminense", (1, 3), ontem.strftime("%Y-%m-%dT%H:%M:00-03:00"),
                               [lance("Goal", "Hulk")])]}
    primeiro_gol._ultimas_consultas.clear()
    with patch("services.importador_espn.consultar_scoreboard", return_value=dados) as consulta:
        assert primeiro_gol.completar_primeiros_marcadores([camp], agora=0) == 1
        assert primeiro_gol.completar_primeiros_marcadores([camp], agora=10) == 0
    assert jogo.primeiro_marcador == "Hulk"
    assert {c.args for c in consulta.call_args_list} == {
        ("bra.1", ontem.strftime("%Y%m%d")), ("bra.1", (ontem - timedelta(days=1)).strftime("%Y%m%d"))}


def test_bonus_desligado_em_todos_os_boloes_nao_consulta_a_espn(app):
    camp, rodada = _campeonato("football-data", "BSA")
    criador = Participante(nome="Admin", email="admin@x.com", admin=True)
    db.session.add(criador)
    db.session.flush()
    db.session.add(Bolao(nome="Sem bônus", campeonato=camp, criador=criador, pontos_primeiro_gol=0))
    ontem = datetime.now() - timedelta(days=1)
    jogo = _jogo(rodada, "Corinthians", "Fluminense", placar=(1, 3), data=ontem)
    db.session.commit()
    dados = {"events": [evento("9", "Corinthians", "Fluminense", (1, 3), ontem.strftime("%Y-%m-%dT%H:%M:00-03:00"),
                               [lance("Goal", "Hulk")])]}
    primeiro_gol._ultimas_consultas.clear()
    with patch("services.importador_espn.consultar_scoreboard", return_value=dados) as consulta:
        assert primeiro_gol.completar_primeiros_marcadores([camp], agora=0) == 0
        consulta.assert_not_called()
        # Basta um bolão do campeonato com o bônus ligado para buscar o marcador.
        db.session.add(Bolao(nome="Com bônus", campeonato=camp, criador=criador))
        db.session.commit()
        assert primeiro_gol.completar_primeiros_marcadores([camp], agora=0) == 1
    assert jogo.primeiro_marcador == "Hulk"


def test_placar_diferente_nao_preenche(app):
    camp, rodada = _campeonato("football-data", "BSA")
    ontem = datetime.now() - timedelta(days=1)
    jogo = _jogo(rodada, "Corinthians", "Fluminense", placar=(2, 3), data=ontem)
    db.session.commit()
    dados = {"events": [evento("9", "Corinthians", "Fluminense", (1, 3), ontem.isoformat() + "-03:00",
                               [lance("Goal", "Hulk")])]}
    primeiro_gol._ultimas_consultas.clear()
    with patch("services.importador_espn.consultar_scoreboard", return_value=dados):
        assert primeiro_gol.completar_primeiros_marcadores([camp], agora=0) == 0
    assert jogo.primeiro_marcador is None


def test_conferencia_classifica_e_aplica_sem_mexer_no_que_confere(app, tmp_path, capsys):
    camp, rodada = _campeonato("football-data", "BSA")
    criador = Participante(nome="Admin", email="admin@x.com", admin=True)
    db.session.add(criador)
    db.session.flush()
    bolao = Bolao(nome="Bolão", campeonato=camp, criador=criador)
    db.session.add(bolao)
    jogo = _jogo(rodada, "Corinthians", "Fluminense", placar=(1, 3))
    _jogo(rodada, "Bahia", "Vitória", classico=False, placar=(1, 0))  # comum: ignorado
    partes = {}
    # nome: (palpite de primeiro gol, crédito histórico da planilha)
    casos = {"Ana": ("Hulk", 2), "Beto": ("Pedro", 2), "Caio": ("hulk", 0), "Davi": (None, 2),
             "Edu": ("Hulk Paraíba", 0)}
    for nome, (previsto, credito) in casos.items():
        pessoa = Participante(nome=nome, email=f"{nome}@x.com")
        db.session.add(pessoa)
        db.session.flush()
        part = Participacao(bolao=bolao, participante_legado=pessoa, nome_exibicao=nome)
        db.session.add(part)
        db.session.add(Palpite(participacao=part, jogo=jogo, gols_casa=0, gols_fora=1, primeiro_gol=previsto))
        if credito:
            db.session.add(BonusRodada(participante_id=pessoa.id, rodada=rodada, participacao=part, pontos=credito))
        partes[nome] = part
    db.session.commit()
    antes = {i["participante"].nome_exibicao: i["pontos"] for i in calcular_ranking(bolao)}

    eventos = [{"external_id": "9", "time_casa": "SC Corinthians Paulista", "time_fora": "Fluminense FC",
                "data": None, "gols_casa": 1, "gols_fora": 3, "tem_detalhes": True, "primeiro_marcador": "Hulk"}]
    relatorio = conferir(bolao, eventos)
    assert [(l["jogo"].id, l["situacao"]) for l in relatorio.jogos] == [(jogo.id, "encontrado")]
    situacoes = {l["participacao"].nome_exibicao: (l["situacao"], l["credito_novo"], l["variacao"])
                 for l in relatorio.pessoas}
    assert situacoes == {"Ana": ("confere", 0, 0), "Beto": ("planilha_maior", 2, 0),
                         "Caio": ("bonus_novo", 0, 2), "Davi": ("inferido", 0, 0)}
    assert [(q["participacao"].nome_exibicao, q["palpite"]) for q in relatorio.quase] == [("Edu", "Hulk Paraíba")]
    assert jogo.primeiro_marcador is None  # simulação não grava
    from scripts.conferir_primeiro_gol import imprimir_resumo, salvar_relatorio
    salvar_relatorio(relatorio, tmp_path)
    imprimir_resumo(relatorio)
    assert "Caio: +2" in capsys.readouterr().out
    assert "Hulk" in (tmp_path / f"bolao{bolao.id}-jogos.csv").read_text(encoding="utf-8-sig")

    assert aplicar(relatorio, "02/11/2026") == (1, 1, 2)
    db.session.commit()
    assert jogo.primeiro_marcador == "Hulk"
    davi = Palpite.query.filter_by(participacao_id=partes["Davi"].id).one()
    assert davi.primeiro_gol == "Hulk" and "conferencia_espn" in davi.logs[-1].valores_novos
    credito_ana = BonusRodada.query.filter_by(participacao_id=partes["Ana"].id).one()
    assert credito_ana.pontos == 0 and "conferido" in credito_ana.motivo
    depois = {i["participante"].nome_exibicao: i["pontos"] for i in calcular_ranking(bolao)}
    assert {n: depois[n] - antes[n] for n in antes} == {"Ana": 0, "Beto": 0, "Caio": 2, "Davi": 0, "Edu": 0}


def test_inferencia_so_quando_o_credito_prova_quais_jogos(app):
    camp, rodada = _campeonato("football-data", "BSA")
    criador = Participante(nome="Admin", email="admin@x.com", admin=True)
    db.session.add(criador)
    db.session.flush()
    bolao = Bolao(nome="Bolão", campeonato=camp, criador=criador)
    db.session.add(bolao)
    jogos = [_jogo(rodada, "Corinthians", "Palmeiras", placar=(1, 0), marcador="Yuri Alberto"),
             _jogo(rodada, "Flamengo", "Vasco", placar=(2, 1), marcador="Pedro"),
             _jogo(rodada, "Grêmio", "Internacional", placar=(0, 0))]  # sem gol: não conta
    for nome, credito in {"Ana": 2, "Beto": 4, "Caio": 6}.items():
        pessoa = Participante(nome=nome, email=f"{nome}@x.com")
        db.session.add(pessoa)
        db.session.flush()
        part = Participacao(bolao=bolao, participante_legado=pessoa, nome_exibicao=nome)
        db.session.add(part)
        for jogo in jogos:
            db.session.add(Palpite(participacao=part, jogo=jogo, gols_casa=1, gols_fora=0))
        db.session.add(BonusRodada(participante_id=pessoa.id, rodada=rodada, participacao=part, pontos=credito))
    db.session.commit()
    relatorio = conferir(bolao, [])
    situacoes = {l["participacao"].nome_exibicao: (l["situacao"], l["credito_novo"], l["variacao"])
                 for l in relatorio.pessoas}
    assert situacoes == {"Ana": ("ambiguo", 2, 0), "Beto": ("inferido", 0, 0), "Caio": ("impossivel", 6, 0)}
    antes = {i["participante"].nome_exibicao: i["pontos"] for i in calcular_ranking(bolao)}
    assert aplicar(relatorio, "02/11/2026") == (0, 2, 1)
    db.session.commit()
    beto = Palpite.query.join(Participacao).filter(Participacao.nome_exibicao == "Beto").all()
    assert sorted(p.primeiro_gol or "" for p in beto) == ["", "Pedro", "Yuri Alberto"]
    depois = {i["participante"].nome_exibicao: i["pontos"] for i in calcular_ranking(bolao)}
    assert depois == antes
