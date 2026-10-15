"""Escopo por bolão e responsáveis pela API (mesmas regras das telas antigas)."""
import pytest
from database import db
from models import Bolao, Campeonato, Jogo, Participacao, Participante, Palpite, PalpiteLog, Resultado, Rodada
from tests.test_acesso_gestao import gestao, sessao  # noqa: F401


def preparar(gestao):
    app, usuarios, bolao_id, pessoa, rodada, jogo = gestao
    usuario = db.session.get(Participante, usuarios['responsavel'])
    a = db.session.get(Bolao, bolao_id)
    b = Bolao(nome=a.nome, campeonato=a.campeonato, criador=usuario)
    outro = Campeonato(nome='Outro', ano=2027)
    c = Bolao(nome='Outro bolão', campeonato=outro, criador=usuario)
    db.session.add_all([Participacao(bolao=b, usuario=usuario, nome_exibicao='Gestor B', papel='responsavel'),
        Participacao(bolao=c, usuario=usuario, nome_exibicao='Gestor C', papel='responsavel')])
    j = Jogo(time_casa='X', time_fora='Y', rodada=Rodada(nome='Rodada 1', campeonato=outro))
    db.session.add(j)
    db.session.commit()
    client = app.test_client()
    sessao(client, usuario.id)
    return client, a, b, c, j


def selecionar(client, bolao):
    return client.post('/interface/selecionar', data={'bolao_id': bolao.id})


def test_palpite_so_no_bolao_selecionado(gestao):
    client, a, b, c, j = preparar(gestao)
    _, _, _, pessoa, rodada, jogo = gestao
    corpo = {'participacaoId': pessoa, 'rodadaId': rodada, 'jogos': {str(jogo): {'casa': '2', 'fora': '1'}}}
    selecionar(client, b)
    assert client.post('/interface/api/palpites', json=corpo).status_code == 404  # pessoa é do bolão A
    selecionar(client, a)
    assert client.post('/interface/api/palpites', json=corpo).status_code == 200
    assert Palpite.query.one().participacao_id == pessoa and PalpiteLog.query.count() == 1


@pytest.mark.parametrize('metodo,url', [('post', '/interface/api/jogos/{j}/resultado'), ('put', '/interface/api/jogos/{j}'),
    ('post', '/interface/api/jogos/{j}/encerrado'), ('delete', '/interface/api/jogos/{j}'),
    ('delete', '/interface/api/rodadas/{r}')])
def test_ids_de_outro_campeonato_bloqueados(gestao, metodo, url):
    client, a, b, c, j = preparar(gestao)
    selecionar(client, a)
    resposta = getattr(client, metodo)(url.format(j=j.id, r=j.rodada_id),
                                       json={'golsCasa': 1, 'golsFora': 0, 'encerrado': True, 'casa': 'X', 'fora': 'Y'})
    assert resposta.status_code == 404
    assert not j.encerrado and Resultado.query.count() == 0 and db.session.get(Jogo, j.id)


def test_responsaveis_adicionar_remover_preservar_e_ultimo(gestao):
    client, a, b, c, j = preparar(gestao)
    selecionar(client, a)
    proprio = Participacao.query.filter_by(bolao_id=a.id, usuario_id=gestao[1]['responsavel']).one()
    url = '/interface/api/responsaveis'
    assert client.delete(f'{url}/{proprio.id}').status_code == 409
    assert proprio.papel == 'responsavel'
    original = Participacao.query.filter_by(bolao_id=a.id, usuario_id=gestao[1]['comum']).one()
    db.session.add(Palpite(participacao=original, jogo_id=gestao[5], gols_casa=1, gols_fora=0))
    db.session.commit()
    assert client.post(url, json={'email': 'comum@teste.com', 'senha': 'ignorada'}).status_code == 201
    assert original.papel == 'responsavel'
    assert Participacao.query.filter_by(bolao_id=b.id, usuario_id=gestao[1]['comum']).count() == 0
    assert client.delete(f'{url}/{original.id}').status_code == 200
    assert original.papel == 'participante' and original.status == 'ativo'
    assert Palpite.query.count() == PalpiteLog.query.count() == 1
    assert client.post(url, json={'email': 'novo@teste.com', 'nome': 'Novo Gestor', 'senha': 'senha123'}).status_code == 201
    novo = Participante.query.filter_by(email='novo@teste.com').one()
    assert not novo.admin_global and not novo.admin
    assert Participacao.query.filter_by(bolao_id=a.id, usuario_id=novo.id).one().papel == 'responsavel'


def test_acesso_removido_e_responsavel_sem_conta_nao_conta_como_substituto(gestao):
    client, a, b, c, j = preparar(gestao)
    selecionar(client, a)
    sem_conta = db.session.get(Participacao, gestao[3])
    sem_conta.papel = 'responsavel'
    db.session.commit()
    proprio = Participacao.query.filter_by(bolao_id=a.id, usuario_id=gestao[1]['responsavel']).one()
    assert client.delete(f'/interface/api/responsaveis/{proprio.id}').status_code == 409
    proprio.papel = 'participante'
    db.session.commit()
    assert selecionar(client, a).status_code == 403
    assert selecionar(client, b).status_code == 303
    assert client.get('/interface/api/dashboard').status_code == 200


def test_sincronizacao_com_a_api_exige_admin_global(gestao):
    client, a, b, c, j = preparar(gestao)
    selecionar(client, a)
    resposta = client.post('/interface/api/campeonato/sincronizar', json={'acao': 'resultados', 'token': 'x'})
    assert resposta.status_code == 403


def test_csrf_nas_gravacoes(gestao):
    client, a, b, c, j = preparar(gestao)
    selecionar(client, a)
    gestao[0].config['WTF_CSRF_ENABLED'] = True
    assert client.post('/interface/api/responsaveis', json={'email': 'comum@teste.com'}).status_code == 403
