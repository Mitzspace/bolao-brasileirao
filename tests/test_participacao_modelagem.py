import json

import pytest

from database import db
from models import Bolao, Campeonato, Participacao, ParticipacaoLog, Rodada, Palpite, PalpiteLog
from services.elegibilidade import participa_na_rodada, palpite_elegivel, entra_no_ranking_da_rodada
from tests.test_acesso_gestao import gestao, sessao


@pytest.fixture
def pessoa(app, participante_teste, campeonato_teste):
    bolao = Bolao(nome="Teste", campeonato=campeonato_teste, criador=participante_teste)
    part = Participacao(bolao=bolao, nome_exibicao="Pessoa")
    rodadas = [Rodada(nome=f"Rodada {n}", campeonato=campeonato_teste) for n in range(1, 5)]
    db.session.add_all([part, *rodadas])
    db.session.commit()
    return part, rodadas


def test_regra_limites_entrada_desistencia_e_correcao(pessoa):
    part, rodadas = pessoa
    assert all(participa_na_rodada(part, r) for r in rodadas)
    part.rodada_entrada = rodadas[1]
    part.status = "desistente"
    part.rodada_desistencia = rodadas[3]
    db.session.commit()
    assert [participa_na_rodada(part, r) for r in rodadas] == [False, True, True, False]
    part.rodada_desistencia = rodadas[2]
    db.session.commit()
    assert [participa_na_rodada(part, r) for r in rodadas] == [False, True, False, False]
    part.status = "ativo"
    part.rodada_desistencia = None
    db.session.commit()
    assert [participa_na_rodada(part, r) for r in rodadas] == [False, True, True, True]
    part.bolao.politica_entrada_tardia = "zero"
    db.session.commit()
    assert all(entra_no_ranking_da_rodada(part, r) for r in rodadas)
    assert not participa_na_rodada(part, rodadas[0])  # Zero no ranking não é pendência anterior à entrada.


def test_log_nome_desistencia_correcao_reativacao_e_rollback(pessoa):
    part, rodadas = pessoa
    part.nome_exibicao = "Nome corrigido"
    db.session.commit()
    log = ParticipacaoLog.query.order_by(ParticipacaoLog.id.desc()).first()
    assert json.loads(log.valores_anteriores)["nome_exibicao"] == "Pessoa"
    assert json.loads(log.valores_novos)["nome_exibicao"] == "Nome corrigido"
    for acao, status, rodada in [("desistencia", "desistente", rodadas[1]),
                                ("correcao", "desistente", rodadas[2]),
                                ("reativacao", "ativo", None)]:
        part.status, part.rodada_desistencia = status, rodada
        db.session.commit()
        log = ParticipacaoLog.query.order_by(ParticipacaoLog.id.desc()).first()
        assert log.acao == acao and log.alterado_em is not None
        assert json.loads(log.valores_novos)["rodada_desistencia_id"] == (rodada.id if rodada else None)
    total = ParticipacaoLog.query.count()
    part.observacao = "Não persistir"
    db.session.flush()
    assert ParticipacaoLog.query.count() == total + 1
    db.session.rollback()
    assert part.observacao is None and ParticipacaoLog.query.count() == total


def test_log_tem_autor_real_da_rota(gestao):
    client = gestao[0].test_client()
    sessao(client, gestao[1]["responsavel"])
    response = client.post(f"/b/{gestao[2]}/participacoes/{gestao[3]}/editar",
                           data={"nome_exibicao": "Nome editado"})
    assert response.status_code == 302
    log = ParticipacaoLog.query.filter_by(participacao_id=gestao[3]).order_by(ParticipacaoLog.id.desc()).first()
    assert log.alterado_por == gestao[1]["responsavel"]


def test_log_imutavel_e_sem_delete_ou_bulk(pessoa):
    log = ParticipacaoLog.query.first()
    log.valores_novos = "{}"
    with pytest.raises(ValueError, match="imutáveis"):
        db.session.commit()
    db.session.rollback()
    db.session.delete(log)
    with pytest.raises(ValueError, match="Histórico"):
        db.session.commit()
    db.session.rollback()
    with pytest.raises(ValueError, match="auditoria"):
        ParticipacaoLog.query.delete()


@pytest.mark.parametrize("campo", ["rodada_entrada", "rodada_desistencia"])
@pytest.mark.parametrize("por_id", [True, False])
def test_recusa_rodada_de_outro_campeonato(pessoa, campo, por_id):
    part, _ = pessoa
    outro = Campeonato(nome="Outro")
    rodada = Rodada(nome="Rodada 1", campeonato=outro)
    db.session.add(rodada)
    db.session.commit()
    setattr(part, campo + "_id" if por_id else campo, rodada.id if por_id else rodada)
    with pytest.raises(ValueError, match="campeonato do bolão"):
        db.session.commit()
    db.session.rollback()


def test_exclusao_de_palpite_persiste_e_tem_log(pessoa):
    from models import Jogo
    part, rodadas = pessoa
    jogo = Jogo(time_casa="A", time_fora="B", rodada=rodadas[0])
    pal = Palpite(participacao=part, jogo=jogo, gols_casa=1, gols_fora=0)
    db.session.add(pal)
    db.session.commit()
    assert palpite_elegivel(pal)
    pal.excluido_por_desistencia = True
    db.session.commit()
    assert not palpite_elegivel(pal)
    log = PalpiteLog.query.order_by(PalpiteLog.id.desc()).first()
    assert json.loads(log.valores_anteriores)["excluido_por_desistencia"] is False
    assert json.loads(log.valores_novos)["excluido_por_desistencia"] is True
    part.status = "ativo"
    part.rodada_desistencia = None
    db.session.commit()
    assert not palpite_elegivel(pal)  # Reativar a pessoa não restaura palpites sem confirmação.
