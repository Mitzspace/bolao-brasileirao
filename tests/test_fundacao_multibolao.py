import json

from types import SimpleNamespace
from flask import g

import pytest
from sqlalchemy.exc import IntegrityError

from database import db
from models import Bolao, Participacao, Palpite, PalpiteLog, Participante, Resultado
from services.pontuacao import calcular_pontuacao
from tests.apoio_lancamento import enviar


def autorizar_responsavel(usuario, jogo):
    bolao = Bolao.query.filter_by(campeonato_id=jogo.rodada.campeonato_id).first()
    if bolao is None:
        bolao = Bolao(nome='Teste', campeonato=jogo.rodada.campeonato, criador=usuario)
        db.session.add(bolao)
    db.session.add(Participacao(bolao=bolao, usuario=usuario,
        participante_legado_id=usuario.id, nome_exibicao=usuario.nome, papel='responsavel'))
    db.session.commit()


def test_auditoria_criacao_correcao_e_rollback(client, admin_teste, participante_teste, jogo_teste):
    autorizar_responsavel(admin_teste, jogo_teste)
    db.session.add(Participacao(bolao=Bolao.query.one(), participante_legado_id=participante_teste.id,
                               nome_exibicao=participante_teste.nome))
    db.session.commit()
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_teste.id)
    g.pop("_login_user", None)
    pessoa = Participacao.query.filter_by(participante_legado_id=participante_teste.id).one()
    form = {"participante_id": pessoa.id, "rodada_id": jogo_teste.rodada_id,
            f"casa_{jogo_teste.id}": "2", f"fora_{jogo_teste.id}": "1"}
    assert enviar(client, form).status_code == 200
    palpite = Palpite.query.one()
    assert palpite.participacao.usuario_id is None
    assert palpite.origem == "responsavel"
    assert palpite.lancado_por == admin_teste.id
    assert palpite.criado_em and palpite.atualizado_em
    log = PalpiteLog.query.one()
    assert log.acao == "criacao" and log.alterado_por == admin_teste.id
    assert json.loads(log.valores_novos)["participacao_id"] == palpite.participacao_id
    form[f"casa_{jogo_teste.id}"] = "3"
    enviar(client, form)
    logs = PalpiteLog.query.order_by(PalpiteLog.id).all()
    assert len(logs) == 2
    assert json.loads(logs[1].valores_anteriores)["gols_casa"] == 2
    assert json.loads(logs[1].valores_novos)["gols_casa"] == 3
    assert palpite.lancado_por == admin_teste.id
    palpite.gols_casa = 5
    db.session.flush()
    assert PalpiteLog.query.count() == 3
    db.session.rollback()
    assert PalpiteLog.query.count() == 2
    assert db.session.get(Palpite, palpite.id).gols_casa == 3


def test_multiplas_pessoas_sem_conta_e_unicidade_usuario(app, participante_teste, campeonato_teste):
    bolao = Bolao(nome="Teste", campeonato=campeonato_teste, criador=participante_teste)
    db.session.add_all([Participacao(bolao=bolao, nome_exibicao="A"), Participacao(bolao=bolao, nome_exibicao="B")])
    db.session.commit()
    assert Participacao.query.count() == 2
    db.session.add(Participacao(bolao=bolao, usuario=participante_teste, nome_exibicao="C"))
    db.session.commit()
    db.session.add(Participacao(bolao=bolao, usuario=participante_teste, nome_exibicao="D"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_mesmo_jogo_em_dois_boloes(app, participante_teste, jogo_teste):
    for nome in ("A", "B"):
        bolao = Bolao(nome=nome, campeonato=jogo_teste.rodada.campeonato, criador=participante_teste)
        db.session.add(bolao)
        part = Participacao(bolao=bolao, usuario=participante_teste, participante_legado_id=participante_teste.id, nome_exibicao=nome)
        db.session.add(Palpite(participacao=part, participante_id=participante_teste.id, jogo=jogo_teste, gols_casa=1, gols_fora=0))
    db.session.commit()
    assert Palpite.query.count() == 2 and PalpiteLog.query.count() == 2


def test_duplicata_por_participacao_impedida(app, participante_teste, jogo_teste):
    original = Palpite(participante_id=participante_teste.id, jogo=jogo_teste, gols_casa=1, gols_fora=0)
    db.session.add(original)
    db.session.commit()
    db.session.add(Palpite(participacao=original.participacao, participante_id=participante_teste.id, jogo=jogo_teste, gols_casa=2, gols_fora=0))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert PalpiteLog.query.count() == 1


def test_conta_desativada_nao_faz_login(client, participante_teste):
    from utils import hash_senha
    participante_teste.senha = hash_senha("segredo123")
    participante_teste.conta_ativa = False
    db.session.commit()
    client.post("/login", data={"email": participante_teste.email, "senha": "segredo123"})
    with client.session_transaction() as sess:
        assert "_user_id" not in sess


def test_logs_e_pessoas_nao_sao_apagados(app, participante_teste, jogo_teste):
    db.session.add(Palpite(participante_id=participante_teste.id, jogo=jogo_teste, gols_casa=1, gols_fora=0))
    db.session.commit()
    log = PalpiteLog.query.one()
    log.valores_novos = "{}"
    with pytest.raises(ValueError, match="imutáveis"):
        db.session.commit()
    db.session.rollback()
    db.session.delete(participante_teste)
    with pytest.raises(ValueError, match="Histórico"):
        db.session.commit()
    db.session.rollback()
    with pytest.raises(ValueError, match="auditoria"):
        Palpite.query.update({"gols_casa": 7})


@pytest.mark.parametrize("entidade", ["jogos", "rodadas"])
def test_exclusao_de_dados_globais_com_historico_e_recusada(client, admin_teste, participante_teste, jogo_teste, entidade):
    autorizar_responsavel(admin_teste, jogo_teste)
    db.session.add(Palpite(participante_id=participante_teste.id, jogo=jogo_teste, gols_casa=1, gols_fora=0))
    db.session.commit()
    ids = {"jogos": jogo_teste.id, "rodadas": jogo_teste.rodada_id}
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_teste.id)
    g.pop("_login_user", None)
    response = client.delete(f"/interface/api/{entidade}/{ids[entidade]}")
    assert response.status_code == 409
    assert Palpite.query.count() == 1 and PalpiteLog.query.count() == 1


@pytest.mark.parametrize("classico", [False, True])
def test_bonus_independente_do_placar_inclusive_gol_contra(classico):
    palpite = Palpite(gols_casa=0, gols_fora=2, primeiro_gol="  João  Silva ")
    jogo = SimpleNamespace(classico=classico, primeiro_marcador="JOAO SILVA")
    resultado = Resultado(gols_casa_real=1, gols_fora_real=0)
    pontos = calcular_pontuacao(palpite, jogo, resultado)
    assert pontos.pontos_placar == 0 and pontos.pontos_bonus == 2 and pontos.total == 2
    resultado.gols_casa_real = resultado.gols_fora_real = 0
    assert calcular_pontuacao(palpite, jogo, resultado).pontos_bonus == 0
    resultado.gols_casa_real = 1
    palpite.primeiro_gol = ""
    assert calcular_pontuacao(palpite, jogo, resultado).pontos_bonus == 0


def test_primeiro_marcador_global_e_adaptador_formulario(app, jogo_teste):
    jogo_teste.especial = True
    resultado = Resultado(jogo=jogo_teste, gols_casa_real=1, gols_fora_real=0, primeiro_gol_real="João")
    db.session.add(resultado)
    db.session.commit()
    assert jogo_teste.classico and jogo_teste._especial_legado
    assert jogo_teste.primeiro_marcador == "João"
    jogo_teste.primeiro_marcador = "Pedro"
    db.session.commit()
    assert resultado.primeiro_gol_real == "Pedro"


def test_app_recusa_schema_antigo_sem_modificar(tmp_path):
    import sqlite3
    from app import create_app
    path = tmp_path / "antigo.db"
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE participante (id INTEGER PRIMARY KEY)")
    antes = path.read_bytes()
    with pytest.raises(RuntimeError, match="migração explícita"):
        create_app("testing", database_uri="sqlite:///" + path.as_posix())
    assert path.read_bytes() == antes
