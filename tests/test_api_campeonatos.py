"""Aba Campeonatos: mesmas regras das telas atuais, agora pela API."""
import json

from database import db
from models import ClassificacaoCache, Jogo, Palpite, Participacao, Resultado, Rodada
from tests.test_interface import entrar, gestao  # noqa: F401


def preparar(client, gestao):
    usuario, boloes = gestao
    bolao = boloes[0]
    r1 = Rodada(nome='Rodada 1', campeonato=bolao.campeonato)
    r2 = Rodada(nome='Rodada 2', campeonato=bolao.campeonato, aberta=False)
    j1 = Jogo(time_casa='Flamengo', time_fora='Vasco', rodada=r1)
    pessoa = Participacao(bolao=bolao, nome_exibicao='Ana')
    db.session.add_all([r1, r2, j1, pessoa])
    db.session.flush()
    db.session.add_all([Resultado(jogo=j1, gols_casa_real=1, gols_fora_real=0),
                        Palpite(participacao=pessoa, jogo=j1, gols_casa=1, gols_fora=0)])
    db.session.commit()
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': bolao.id})
    return bolao, r1, r2


def test_listagem_do_campeonato(client, gestao):
    bolao, r1, r2 = preparar(client, gestao)
    dados = client.get('/interface/api/campeonato').get_json()
    assert dados['campeonato']['id'] == bolao.campeonato_id
    assert dados['campeonato']['rodadasConcluidas'] == 1 and dados['campeonato']['totalRodadas'] == 2
    rodadas = {r['nome']: r for r in dados['rodadas']}
    assert rodadas['Rodada 1']['podeExcluir'] is False  # tem palpite
    assert rodadas['Rodada 2']['podeExcluir'] is True and rodadas['Rodada 2']['estado'] == 'sem_jogos'
    assert rodadas['Rodada 1']['estado'] == 'fechada'
    assert rodadas['Rodada 1']['links']['palpites'].startswith(f'/b/{bolao.id}/')
    assert dados['adminGlobal'] is False and 'sync' not in dados['links']
    assert not any('importar' in k.lower() for k in dados['links'])
    assert dados['campeonatosDoBolao'] == [{'bolaoId': bolao.id, 'nome': bolao.campeonato.nome,
                                            'ano': bolao.campeonato.ano, 'atual': True}]


def test_editar_campeonato_valida_e_salva(client, gestao):
    bolao, *_ = preparar(client, gestao)
    resposta = client.put('/interface/api/campeonato', json={'nome': '', 'ano': 2026, 'codigoApi': 'BSA'})
    assert resposta.status_code == 400 and 'Nome' in resposta.get_json()['erro']
    resposta = client.put('/interface/api/campeonato', json={'nome': 'Brasileirão', 'ano': 'x', 'codigoApi': 'BSA'})
    assert resposta.status_code == 400
    resposta = client.put('/interface/api/campeonato', json={'nome': 'Brasileirão', 'ano': 2026, 'codigoApi': 'b s'})
    assert resposta.status_code == 400
    resposta = client.put('/interface/api/campeonato', json={'nome': 'Série A', 'ano': 2027, 'codigoApi': 'bsa'})
    assert resposta.status_code == 200
    db.session.refresh(bolao.campeonato)
    assert (bolao.campeonato.nome, bolao.campeonato.ano, bolao.campeonato.codigo_api) == ('Série A', 2027, 'BSA')


def test_rodadas_criar_e_excluir(client, gestao):
    bolao, r1, r2 = preparar(client, gestao)
    nova = client.post('/interface/api/rodadas', json={'nome': 'Rodada 3', 'aberta': True})
    assert nova.status_code == 201
    nova_id = nova.get_json()['rodadaId']
    bloqueada = client.delete(f'/interface/api/rodadas/{r1.id}')
    assert bloqueada.status_code == 409 and 'não pode ser excluída' in bloqueada.get_json()['erro']
    assert client.delete(f'/interface/api/rodadas/{nova_id}').status_code == 200
    assert db.session.get(Rodada, nova_id) is None and db.session.get(Rodada, r1.id) is not None


def test_rodada_de_outro_bolao_nao_pode_ser_alterada(client, gestao):
    preparar(client, gestao)
    _, boloes = gestao
    alheia = Rodada(nome='Rodada X', campeonato=boloes[2].campeonato)
    db.session.add(alheia)
    db.session.commit()
    assert client.delete(f'/interface/api/rodadas/{alheia.id}').status_code == 404
    assert db.session.get(Rodada, alheia.id).aberta is True


def test_gravacoes_exigem_csrf(client, gestao, app):
    preparar(client, gestao)
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.put('/interface/api/campeonato', json={'nome': 'X', 'ano': 1}).status_code == 403
    assert client.post('/interface/api/rodadas', json={'nome': 'R'}).status_code == 403


def test_tabela_oficial_pelo_cache(client, gestao, app):
    bolao, *_ = preparar(client, gestao)
    app.config['FOOTBALL_DATA_TOKEN'] = ''
    payload = {'competition': {'name': 'Campeonato Brasileiro Série A', 'code': 'BSA'},
               'season': {'startDate': '2026-04-01'},
               '_cache_competicao': 'BSA', '_cache_temporada': '2026',
               'standings': [{'type': 'TOTAL', 'table': [
                   {'position': 1, 'team': {'id': 1783, 'name': 'CR Flamengo', 'shortName': 'Flamengo', 'tla': 'FLA'},
                    'points': 60, 'playedGames': 29, 'won': 18, 'draw': 6, 'lost': 5,
                    'goalsFor': 50, 'goalsAgainst': 20, 'goalDifference': 30}]}]}
    db.session.add(ClassificacaoCache(campeonato_id=bolao.campeonato_id, dados_json=json.dumps(payload)))
    db.session.commit()
    dados = client.get('/interface/api/tabela').get_json()
    linha = dados['grupos'][0]['linhas'][0]
    assert dados['sucesso'] and linha['time'] == 'Flamengo' and linha['pontos'] == 60
    assert linha['zona']['nome'] == 'Fase de Grupos Libertadores'
    assert linha['escudo']['fontes'][0] == '/static/escudos/flamengo.png'


def test_tela_antiga_continua_funcionando(client, gestao):
    """Rotas antigas agora usam o mesmo serviço; o comportamento é o mesmo."""
    bolao, r1, r2 = preparar(client, gestao)
    resposta = client.post(f'/b/{bolao.id}/rodada/{r1.id}/excluir')
    assert resposta.status_code == 302 and db.session.get(Rodada, r1.id) is not None
    client.post(f'/b/{bolao.id}/rodada/{r2.id}/toggle-aberta')
    assert db.session.get(Rodada, r2.id).aberta is True
    client.post(f'/b/{bolao.id}/campeonato/{bolao.campeonato_id}/editar', data={'nome': 'Novo nome', 'ano': '2030'})
    assert bolao.campeonato.nome == 'Novo nome' and bolao.campeonato.ano == 2030
