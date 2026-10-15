"""Desistências pela API da interface: mesmas regras de prévia, confirmação e histórico."""
from datetime import datetime

import pytest
from database import db
from models import Bolao, Jogo, Palpite, PalpiteLog, Participacao, ParticipacaoLog, Resultado, Rodada
from tests.test_acesso_gestao import gestao, sessao
from services.ranking import calcular_ranking
from services.elegibilidade import participa_na_rodada, entra_no_ranking_da_rodada
from services.resumo_boloes import participantes_pendentes


@pytest.fixture
def ciclo(gestao):
    app, usuarios, bolao, pessoa, primeira, jogo = gestao
    rodadas = [db.session.get(Rodada, primeira)]
    for numero in (2, 3):
        rodada = Rodada(nome=f'Rodada {numero}', campeonato_id=rodadas[0].campeonato_id)
        db.session.add(rodada)
        db.session.flush()
        db.session.add(Jogo(time_casa=f'Casa {numero}', time_fora=f'Fora {numero}', rodada=rodada, data=datetime(2026, 1, 1)))
        rodadas.append(rodada)
    db.session.flush()
    for rodada in rodadas:
        partida = Jogo.query.filter_by(rodada_id=rodada.id).one()
        db.session.add_all([Palpite(participacao_id=pessoa, jogo_id=partida.id, gols_casa=2, gols_fora=1),
            Resultado(jogo_id=partida.id, gols_casa_real=2, gols_fora_real=1)])
    db.session.commit()
    client = app.test_client()
    sessao(client, usuarios['responsavel'])
    return app, client, bolao, pessoa, [r.id for r in rodadas]


def previa(ciclo, acao='registrar', indice=1):
    app, client, bolao, pessoa, rodadas = ciclo
    url = f'/interface/api/participantes/{pessoa}/desistencia'
    dados = {'acao': acao, 'rodadaId': rodadas[indice], 'motivo': 'Motivo de teste'}
    resposta = client.post(url, json=dados)
    assert resposta.status_code == 200, resposta.text
    dados.update(confirmar=True, token=resposta.get_json()['token'])
    return url, dados


def confirmar(ciclo, acao='registrar', indice=1, restaurar='sim'):
    url, dados = previa(ciclo, acao, indice)
    dados['restaurar'] = restaurar
    assert ciclo[1].post(url, json=dados).status_code == 200


def ranking(bolao, rodada=None, ocultar=False):
    alvo = db.session.get(Bolao, bolao)
    return calcular_ranking(alvo, db.session.get(Rodada, rodada) if rodada else None, ocultar)


def test_previa_preserva_e_confirmacao_exclui_apenas_futuro(ciclo):
    app, client, bolao, pessoa, rodadas = ciclo
    quantidade = PalpiteLog.query.count()
    valores = [(p.id, p.gols_casa, p.gols_fora, p.lancado_apos_inicio) for p in Palpite.query.order_by(Palpite.id)]
    url, dados = previa(ciclo)
    assert db.session.get(Participacao, pessoa).status == 'ativo'
    assert PalpiteLog.query.count() == quantidade
    assert client.post(url, json=dados).status_code == 200
    part = db.session.get(Participacao, pessoa)
    assert part.status == 'desistente' and part.rodada_desistencia_id == rodadas[1]
    assert part.desistencia_registrada_em and part.desistencia_registrada_por
    assert [(p.id, p.gols_casa, p.gols_fora, p.lancado_apos_inicio) for p in Palpite.query.order_by(Palpite.id)] == valores
    assert [p.excluido_por_desistencia for p in Palpite.query.order_by(Palpite.id)] == [False, True, True]
    assert PalpiteLog.query.count() == quantidade + 2
    assert ParticipacaoLog.query.filter_by(participacao_id=pessoa, acao='desistencia').count() == 1
    assert next(r for r in ranking(bolao) if r['participante'].id == pessoa)['pontos'] == 3
    for rodada, presente in [(rodadas[0], True), (rodadas[1], False), (rodadas[2], False)]:
        assert (pessoa in [r['participante'].id for r in ranking(bolao, rodada)]) == presente
    assert pessoa not in [r['participante'].id for r in ranking(bolao, ocultar=True)]
    assert not participa_na_rodada(part, db.session.get(Rodada, rodadas[1]))
    assert pessoa not in [r['participacao'].id for r in participantes_pendentes(part.bolao, db.session.get(Rodada, rodadas[1]))]
    assert client.post('/interface/api/palpites', json={'participacaoId': pessoa, 'rodadaId': rodadas[1]}).status_code == 409


def test_corrigir_rodada_e_reativar_com_resultado_oficial(ciclo):
    confirmar(ciclo)
    confirmar(ciclo, 'corrigir', 2)
    assert [p.excluido_por_desistencia for p in Palpite.query.order_by(Palpite.id)] == [False, False, True]
    confirmar(ciclo, 'corrigir', 0)
    assert all(p.excluido_por_desistencia for p in Palpite.query.all())
    confirmar(ciclo, 'reativar')
    part = db.session.get(Participacao, ciclo[3])
    assert part.status == 'ativo' and part.rodada_desistencia_id is None
    assert not any(p.excluido_por_desistencia for p in Palpite.query.all())
    Resultado.query.first().gols_casa_real = 0
    db.session.commit()
    assert next(r for r in ranking(ciclo[2]) if r['participante'].id == part.id)['pontos'] == 6
    assert ParticipacaoLog.query.filter_by(participacao_id=part.id, acao='reativacao').count() == 1


def test_reativar_exige_decisao_e_permite_restauracao_posterior(ciclo):
    confirmar(ciclo)
    url, dados = previa(ciclo, 'reativar')
    assert ciclo[1].post(url, json=dados).status_code == 422
    dados['restaurar'] = 'nao'
    assert ciclo[1].post(url, json=dados).status_code == 200
    assert Palpite.query.filter_by(excluido_por_desistencia=True).count() == 2
    confirmar(ciclo, 'restaurar')
    assert Palpite.query.filter_by(excluido_por_desistencia=True).count() == 0


@pytest.mark.parametrize('mudanca', ['token', 'palpite', 'rodada'])
def test_previa_adulterada_ou_desatualizada_nao_grava(ciclo, mudanca):
    url, dados = previa(ciclo)
    if mudanca == 'token':
        dados['token'] = 'invalido'
    elif mudanca == 'rodada':
        dados['rodadaId'] = ciclo[4][2]
    else:
        Palpite.query.first().gols_casa = 4
        db.session.commit()
    assert ciclo[1].post(url, json=dados).status_code == 409
    assert db.session.get(Participacao, ciclo[3]).status == 'ativo'
    assert not any(p.excluido_por_desistencia for p in Palpite.query.all())


def test_validacao_entrada_permissao_e_importacao(ciclo):
    part = db.session.get(Participacao, ciclo[3])
    part.rodada_entrada_id = ciclo[4][1]
    db.session.commit()
    url = f'/interface/api/participantes/{part.id}/desistencia'
    assert ciclo[1].post(url, json={'acao': 'registrar', 'rodadaId': ciclo[4][0]}).status_code == 422
    for politica in ('zero', 'fora_da_conta'):
        part.bolao.politica_entrada_tardia = politica
        db.session.commit()
        assert not participa_na_rodada(part, db.session.get(Rodada, ciclo[4][0]))
        assert entra_no_ranking_da_rodada(part, db.session.get(Rodada, ciclo[4][0])) == (politica == 'zero')
    confirmar(ciclo)
    Palpite.query.order_by(Palpite.id.desc()).first().gols_casa = 5
    with pytest.raises(ValueError):
        db.session.commit()
    db.session.rollback()
    comum = Participacao.query.filter_by(nome_exibicao='comum').one().usuario_id
    sessao(ciclo[1], comum)
    assert ciclo[1].post(url, json={'acao': 'registrar'}).status_code == 403
