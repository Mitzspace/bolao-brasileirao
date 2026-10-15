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
    assert dados['adminGlobal'] is False and dados['links'] == {}
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


def test_sincronizar_com_a_api_so_admin_geral_e_usa_campeonato_do_bolao(client, gestao, monkeypatch):
    usuario, boloes = gestao
    bolao, *_ = preparar(client, gestao)
    bolao.campeonato.codigo_api = 'BSA'
    db.session.commit()
    assert client.post('/interface/api/campeonato/sincronizar', json={'acao': 'resultados', 'token': 't'}).status_code == 403
    usuario.admin_global = True
    db.session.commit()
    chamadas = []
    def falso(**kw):
        chamadas.append(kw)
        return {'atualizados': 3, 'horarios_atualizados': 1, 'resultados_salvos': 2, 'ignorados': 0}
    monkeypatch.setattr('services.sync.sync_informacoes_jogos', falso)
    r = client.post('/interface/api/campeonato/sincronizar', json={'acao': 'informacoes', 'token': 't'})
    assert r.status_code == 200 and '3 jogos' in r.get_json()['mensagem']
    assert chamadas[0]['campeonato_id'] == bolao.campeonato_id and chamadas[0]['competicao'] == 'BSA'
    assert chamadas[0]['temporada'] == str(bolao.campeonato.ano)
    assert client.get('/interface/api/campeonato').get_json()['adminGlobal'] is True
