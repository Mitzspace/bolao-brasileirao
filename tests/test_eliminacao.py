import pytest

from database import db
from models import BonusRodada, CorteEliminacao, Jogo, Palpite, Participacao, Resultado, Rodada
from services.eliminacao import participacoes_eliminadas
from services.ranking import calcular_ranking
from services.publico import classificacao
from services.evolucao_ranking import evolucao
from tests.apoio import estrutura


@pytest.fixture
def disputa(participante_teste, campeonato_teste):
    bolao, primeiro = estrutura(participante_teste, campeonato_teste, 'Copa')
    bolao.eliminacao_participantes = True
    primeiro.nome_exibicao = 'Ana'
    pessoas = [primeiro] + [Participacao(bolao=bolao, nome_exibicao=n) for n in ['Bia', 'Caio']]
    rodadas = [Rodada(nome=f'Rodada {n}', campeonato=campeonato_teste) for n in [1, 2, 10]]
    jogos = [Jogo(rodada=r, time_casa='A', time_fora='B') for r in rodadas]
    db.session.add_all(pessoas + rodadas + jogos)
    db.session.flush()
    for j in jogos:
        db.session.add(Resultado(jogo=j, gols_casa_real=2, gols_fora_real=0))
    for p, placar in zip(pessoas, [(2, 0), (1, 0), (0, 1)]):
        db.session.add(Palpite(participacao=p, jogo=jogos[0], gols_casa=placar[0], gols_fora=placar[1]))
    corte = CorteEliminacao(bolao=bolao, rodada=rodadas[1], classificados=2)
    db.session.add(corte)
    db.session.commit()
    return bolao, pessoas, rodadas, jogos, corte


def ids(bolao, **kwargs):
    return [i['participante'].id for i in calcular_ranking(bolao, **kwargs)]


def test_desligada_sem_cortes(disputa):
    b, ps, _, _, c = disputa
    b.eliminacao_participantes = False
    assert participacoes_eliminadas(b, ps) == {}
    assert len(ids(b)) == 3
    b.eliminacao_participantes = True
    b.cortes_eliminacao.remove(c)
    assert participacoes_eliminadas(b, ps) == {}


@pytest.mark.parametrize('indice', [0, 1])
def test_pendencias_anteriores_bloqueiam_todos_os_cortes(disputa, indice):
    b, ps, rs, js, _ = disputa
    db.session.add(CorteEliminacao(bolao=b, rodada=rs[2], classificados=1))
    js[indice].encerrado = True
    db.session.delete(js[indice].resultado)
    db.session.commit()
    db.session.expire_all()
    assert participacoes_eliminadas(b, ps) == {}


def test_ranking_geral_rodada_historico_e_publico(disputa):
    b, ps, rs, js, c = disputa
    db.session.delete(js[2].resultado)
    b.rodada_publica = rs[0]
    db.session.commit()
    db.session.expire_all()
    assert participacoes_eliminadas(b, ps) == {ps[2].id: c}
    assert ids(b) == [ps[0].id, ps[1].id]
    for r in rs[:2]:
        assert ps[2].id in ids(b, rodada=r)
    assert ps[2].id not in ids(b, rodada=rs[2])
    assert ps[2].id in ids(b, ate_rodada=rs[0])
    assert classificacao(b)['eliminadosOcultos'] == 0
    b.rodada_publica = rs[1]
    assert classificacao(b)['eliminadosOcultos'] == 1
    assert len(classificacao(b)['itens']) == 2
    assert classificacao(b, numero=2)['eliminadosOcultos'] == 0


def test_cumulativo_ordem_numerica_e_evolucao(disputa):
    b, ps, rs, js, c = disputa
    segundo = CorteEliminacao(bolao=b, rodada=rs[2], classificados=1)
    db.session.add(segundo)
    db.session.add(Palpite(participacao=ps[2], jogo=js[2], gols_casa=2, gols_fora=0))
    db.session.commit()
    b.cortes_eliminacao.reverse()
    assert participacoes_eliminadas(b, ps) == {ps[2].id: c, ps[1].id: segundo}
    assert ids(b) == [ps[0].id]
    assert ids(b, todos=[ps[1]]) == []  # filtro não muda os adversários do corte
    linhas = evolucao(b)
    assert linhas[ps[2].id][1]['posicao'] is None
    assert linhas[ps[2].id][2]['participa'] is False


def test_regras_creditos_e_elegibilidade(disputa):
    b, ps, rs, _, c = disputa
    b.pontos_comum_resultado = 8
    b.pontos_comum_exato = 10
    credito = BonusRodada(participacao=ps[2], participante_id=b.criador_id, rodada=rs[0], pontos=9)
    db.session.add(credito)
    db.session.commit()
    assert participacoes_eliminadas(b, ps) == {ps[1].id: c}
    ps[2].rodada_entrada = rs[1]
    assert participacoes_eliminadas(b, ps) == {ps[2].id: c}
    ps[2].rodada_entrada = None
    ps[2].status = 'desistente'
    ps[2].rodada_desistencia = rs[0]
    # Desistente antes do corte não disputa nem ocupa vaga: Ana e Bia seguem.
    assert participacoes_eliminadas(b, ps) == {}


def test_desempate_cravadas_acertos_nome(disputa):
    b, ps, rs, _, c = disputa
    for p, pontos in zip(ps, [7, 9, 10]):
        db.session.add(BonusRodada(participacao=p, participante_id=b.criador_id, rodada=rs[0], pontos=pontos))
    db.session.commit()
    assert participacoes_eliminadas(b, ps) == {ps[2].id: c}
    c.classificados = 1
    assert set(participacoes_eliminadas(b, ps)) == {ps[1].id, ps[2].id}
    for p, nome in zip(ps, ['Zulu', 'Bruno', 'Álvaro']):
        p.nome_exibicao = nome
        p.palpites[0].gols_casa, p.palpites[0].gols_fora = 0, 1
        p.creditos_historicos[0].pontos = 10
    assert set(participacoes_eliminadas(b, ps)) == {ps[0].id, ps[1].id}


def test_desistente_nao_disputa_nem_ocupa_vaga(disputa):
    b, ps, rs, _, _ = disputa
    ps[0].status = 'desistente'
    ps[0].rodada_desistencia = rs[1]
    db.session.commit()
    # Ana desistiu antes do corte: Bia e Caio ficam com as duas vagas.
    assert participacoes_eliminadas(b, ps) == {}


def test_desistente_depois_do_corte_disputa_normalmente(disputa):
    b, ps, rs, _, c = disputa
    ps[0].status = 'desistente'
    ps[0].rodada_desistencia = rs[2]
    db.session.commit()
    assert participacoes_eliminadas(b, ps) == {ps[2].id: c}


def test_entrada_tardia_pode_se_classificar(disputa):
    b, ps, rs, js, c = disputa
    ps[2].rodada_entrada = rs[1]
    db.session.add(Palpite(participacao=ps[2], jogo=js[1], gols_casa=2, gols_fora=0))
    db.session.commit()
    assert ps[2].id not in participacoes_eliminadas(b, ps)
