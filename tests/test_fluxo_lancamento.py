"""Fluxo de lançamento pela API: próximo pendente, pendências, memória da rodada e navegação."""
import pytest
from database import db
from models import Participacao, Palpite, Rodada, Bolao, Campeonato
from tests.test_acesso_gestao import gestao, sessao  # noqa: F401


@pytest.fixture
def fluxo(gestao):
    app, usuarios, bolao, pessoa, rodada, jogo = gestao
    db.session.get(Participacao, pessoa).nome_exibicao = 'B'
    outros = []
    for nome in ('A', 'C', 'D', 'E'):
        p = Participacao(nome_exibicao=nome, bolao_id=bolao)
        db.session.add(p)
        outros.append(p)
    db.session.flush()
    db.session.add(Palpite(participacao_id=outros[2].id, jogo_id=jogo, gols_casa=1, gols_fora=0))
    outros[3].status = 'desistente'
    outros[3].rodada_desistencia_id = rodada
    db.session.commit()
    client = app.test_client()
    sessao(client, usuarios['responsavel'])
    return app, client, bolao, pessoa, rodada, jogo, [p.id for p in outros], usuarios


def salvar(f, pessoa=None, acao='proximo', casa='2'):
    return f[1].post('/interface/api/palpites', json={'participacaoId': pessoa or f[3], 'rodadaId': f[4],
                     'acao': acao, 'jogos': {str(f[5]): {'casa': casa, 'fora': '1'}}})


def tela(f, **params):
    resposta = f[1].get('/interface/api/palpites', query_string=params)
    assert resposta.status_code == 200
    return resposta.get_json()


def test_proximo_pula_completos_desistentes_e_retorna_inicio(fluxo):
    f = fluxo
    assert salvar(f).get_json()['proximoId'] == f[6][1]  # B -> C
    # Completa os dois participantes da fixture, para observar a volta ao A.
    for p in Participacao.query.filter(Participacao.bolao_id == f[2], Participacao.usuario_id.isnot(None)):
        db.session.add(Palpite(participacao_id=p.id, jogo_id=f[5], gols_casa=0, gols_fora=0))
    db.session.commit()
    assert salvar(f, f[6][1]).get_json()['proximoId'] == f[6][0]
    ultimo = salvar(f, f[6][0]).get_json()
    assert ultimo['proximoId'] is None
    assert any('Todos os participantes elegíveis estão completos' in a for a in ultimo['avisos'])


def test_ficar_erro_e_pendencias(fluxo):
    f = fluxo
    assert salvar(f, acao='ficar').get_json()['proximoId'] is None
    assert salvar(f, casa='inválido').status_code == 422
    assert Palpite.query.filter_by(participacao_id=f[3]).one().gols_casa == 2
    dados = tela(f, rodada_id=f[4])
    faltantes = {p['id']: p['faltantes'] for p in dados['participantes']}
    assert faltantes[f[6][0]] == 1 and faltantes[f[6][2]] == 0  # A pendente, D completo
    assert f[6][3] not in faltantes  # desistente fora da rodada
    assert dados['pessoa']['id'] == f[6][0]  # abre no primeiro pendente


def test_memoria_por_admin_e_bolao_e_rodada_padrao(fluxo):
    f = fluxo
    outra = Rodada(nome='Rodada 2', campeonato_id=db.session.get(Bolao, f[2]).campeonato_id)
    db.session.add(outra)
    db.session.commit()
    assert tela(f)['rodada']['id'] == f[4]
    tela(f, rodada_id=outra.id)
    assert tela(f)['rodada']['id'] == outra.id
    db.session.add(Participacao(bolao_id=f[2], usuario_id=f[7]['global'], nome_exibicao='Admin 2', papel='responsavel'))
    db.session.commit()
    sessao(f[1], f[7]['global'])
    assert tela(f)['rodada']['id'] == f[4]
    sessao(f[1], f[7]['responsavel'])
    assert tela(f)['rodada']['id'] == outra.id
    camp = Campeonato(nome='Outro', ano=2026)
    bolao = Bolao(nome='Outro', campeonato=camp, criador_id=f[7]['responsavel'])
    db.session.add(Participacao(bolao=bolao, usuario_id=f[7]['responsavel'], nome_exibicao='Admin', papel='responsavel'))
    db.session.commit()
    f[1].post('/interface/selecionar', data={'bolao_id': bolao.id})
    assert tela(f)['rodada'] is None


def test_navegacao_elegivel_na_rodada(fluxo):
    f = fluxo
    pessoa = tela(f, rodada_id=f[4], participacao_id=f[3])['pessoa']
    assert pessoa['anteriorId'] == f[6][0]
    assert pessoa['proximaId'] == f[6][1]
    db.session.get(Participacao, f[6][1]).rodada_entrada = Rodada(nome='Rodada 2', campeonato_id=db.session.get(Bolao, f[2]).campeonato_id)
    db.session.commit()
    assert salvar(f).get_json()['proximoId'] != f[6][1]
