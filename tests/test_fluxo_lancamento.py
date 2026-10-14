from urllib.parse import urlparse, parse_qs
import pytest
from database import db
from models import Participacao, Palpite, Rodada, Bolao, Campeonato
from tests.test_acesso_gestao import gestao, sessao
from tests.test_ranking_privacidade import contextos


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
    return f[1].post(f'/b/{f[2]}/palpites', data={'participante_id': pessoa or f[3],
        'rodada_id': f[4], 'acao': acao, f'casa_{f[5]}': casa, f'fora_{f[5]}': '1'})


def destino(resposta):
    assert resposta.status_code == 302
    return int(parse_qs(urlparse(resposta.location).query)['participante_id'][0])


def test_proximo_pula_completos_desistentes_e_retorna_inicio(fluxo):
    f = fluxo
    assert destino(salvar(f)) == f[6][1]  # B -> C
    # Completa os dois participantes da fixture, para observar a volta ao A.
    for p in Participacao.query.filter(Participacao.bolao_id == f[2], Participacao.usuario_id.isnot(None)):
        db.session.add(Palpite(participacao_id=p.id, jogo_id=f[5], gols_casa=0, gols_fora=0))
    db.session.commit()
    assert destino(salvar(f, f[6][1])) == f[6][0]
    assert destino(salvar(f, f[6][0])) == f[6][0]
    with f[1].session_transaction() as s:
        assert any('Todos os participantes elegíveis estão completos' in msg for _, msg in s['_flashes'])


def test_ficar_erro_e_links_de_pendencias(fluxo):
    f = fluxo
    assert destino(salvar(f, acao='ficar')) == f[3]
    assert salvar(f, casa='inválido').status_code == 422
    assert Palpite.query.filter_by(participacao_id=f[3]).one().gols_casa == 2
    ctx = contextos(f[0], f[1], f'/b/{f[2]}/palpites?rodada_id={f[4]}')
    ids = [p['participacao'].id for p in ctx['pendentes']]
    assert f[6][0] in ids and f[6][3] not in ids and f[6][2] not in ids
    resposta = f[1].get(f'/b/{f[2]}/palpites?rodada_id={f[4]}')
    assert f'participante_id={f[6][0]}' in resposta.text


def test_memoria_por_admin_e_bolao_e_rodada_padrao(fluxo):
    f = fluxo
    outra = Rodada(nome='Rodada 2', campeonato_id=db.session.get(Bolao, f[2]).campeonato_id)
    db.session.add(outra)
    db.session.commit()
    url = f'/b/{f[2]}/palpites'
    assert contextos(f[0], f[1], url)['rodada_id'] == f[4]
    assert f[1].get(url, query_string={'rodada_id': outra.id}).status_code == 200
    assert contextos(f[0], f[1], url)['rodada_id'] == outra.id
    db.session.add(Participacao(bolao_id=f[2], usuario_id=f[7]['global'], nome_exibicao='Admin 2', papel='responsavel'))
    db.session.commit()
    sessao(f[1], f[7]['global'])
    assert contextos(f[0], f[1], url)['rodada_id'] == f[4]
    sessao(f[1], f[7]['responsavel'])
    assert contextos(f[0], f[1], url)['rodada_id'] == outra.id
    camp = Campeonato(nome='Outro', ano=2026)
    bolao = Bolao(nome='Outro', campeonato=camp, criador_id=f[7]['responsavel'])
    db.session.add(Participacao(bolao=bolao, usuario_id=f[7]['responsavel'], nome_exibicao='Admin', papel='responsavel'))
    db.session.commit()
    assert contextos(f[0], f[1], f'/b/{bolao.id}/palpites')['rodada_id'] is None


def test_navegacao_elegivel_na_rodada(fluxo):
    f = fluxo
    url = f'/b/{f[2]}/palpites?rodada_id={f[4]}&participante_id={f[3]}'
    ctx = contextos(f[0], f[1], url)
    assert ctx['pessoa_anterior'] == f[6][0]
    assert ctx['pessoa_proxima'] == f[6][1]
    assert ctx['rodada_anterior'] is None
    db.session.get(Participacao, f[6][1]).rodada_entrada = Rodada(nome='Rodada 2', campeonato_id=db.session.get(Bolao, f[2]).campeonato_id)
    db.session.commit()
    assert destino(salvar(f)) != f[6][1]
