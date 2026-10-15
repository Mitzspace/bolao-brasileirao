"""Aba Rodadas: jogos e resultados pela API, com as mesmas regras das telas atuais."""
from database import db
from models import Jogo, Palpite, Participacao, Resultado, Rodada
from services.ranking import calcular_ranking
from tests.test_interface import entrar, gestao  # noqa: F401


def preparar(client, gestao):
    usuario, boloes = gestao
    bolao = boloes[0]
    r1 = Rodada(nome='Rodada 1', campeonato=bolao.campeonato)
    classico = Jogo(time_casa='Grêmio', time_fora='Inter', rodada=r1, classico=True)
    comum = Jogo(time_casa='Santos', time_fora='Vasco', rodada=r1)
    ana = Participacao(bolao=bolao, nome_exibicao='Ana')
    db.session.add_all([classico, comum, ana])
    db.session.flush()
    db.session.add(Palpite(participacao=ana, jogo=classico, gols_casa=2, gols_fora=1, primeiro_gol='Braithwaite'))
    db.session.commit()
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': bolao.id})
    return bolao, r1, classico, comum, ana


def test_lista_jogos_da_rodada(client, gestao):
    bolao, r1, classico, comum, ana = preparar(client, gestao)
    dados = client.get('/interface/api/rodadas').get_json()
    assert dados['rodada']['id'] == r1.id and dados['rodada']['participantes'] == 2
    jogos = {j['id']: j for j in dados['jogos']}
    assert jogos[classico.id]['palpites'] == 1 and jogos[classico.id]['podeExcluir'] is False
    assert jogos[comum.id]['podeExcluir'] is True and jogos[comum.id]['classico'] is False


def test_resultado_pontua_igual_a_tela_antiga(client, gestao):
    bolao, r1, classico, comum, ana = preparar(client, gestao)
    resposta = client.post(f'/interface/api/jogos/{classico.id}/resultado',
                           json={'golsCasa': 2, 'golsFora': 1, 'primeiroGol': 'Braithwaite'})
    assert resposta.status_code == 200
    db.session.refresh(classico)
    assert classico.primeiro_marcador == 'Braithwaite'  # auditoria sincroniza o campo da pontuação
    pontos = {i['participante'].nome: i['pontos'] for i in calcular_ranking(bolao)}
    assert pontos['Ana'] == 5 + 2  # placar exato de clássico + primeiro gol
    # Jogo comum não recebe primeiro gol, como na tela atual.
    client.post(f'/interface/api/jogos/{comum.id}/resultado', json={'golsCasa': 0, 'golsFora': 0, 'primeiroGol': 'X'})
    assert comum.resultado.primeiro_gol_real is None
    assert client.post(f'/interface/api/jogos/{comum.id}/resultado', json={'golsCasa': -1, 'golsFora': 0}).status_code == 400


def test_criar_editar_encerrar_e_excluir_jogo(client, gestao):
    bolao, r1, classico, comum, ana = preparar(client, gestao)
    novo = client.post('/interface/api/jogos', json={'casa': 'Remo', 'fora': 'Bahia', 'rodadaId': r1.id,
                                                    'data': '2030-05-02T16:00', 'classico': False})
    assert novo.status_code == 201
    jogo_id = novo.get_json()['id']
    assert client.post('/interface/api/jogos', json={'casa': '', 'fora': 'B', 'rodadaId': r1.id}).status_code == 400
    assert client.put(f'/interface/api/jogos/{jogo_id}', json={'casa': 'Clube do Remo', 'fora': 'Bahia',
                      'rodadaId': r1.id, 'data': 'xx', 'classico': True}).status_code == 400
    assert client.put(f'/interface/api/jogos/{jogo_id}', json={'casa': 'Clube do Remo', 'fora': 'Bahia',
                      'rodadaId': r1.id, 'data': '', 'classico': True}).status_code == 200
    jogo = db.session.get(Jogo, jogo_id)
    assert jogo.time_casa == 'Clube do Remo' and jogo.classico and jogo.data is None
    client.post(f'/interface/api/jogos/{jogo_id}/encerrado', json={'encerrado': True})
    assert jogo.encerrado
    client.post(f'/interface/api/jogos/{jogo_id}/encerrado', json={'encerrado': False})
    assert not jogo.encerrado
    bloqueado = client.delete(f'/interface/api/jogos/{classico.id}')
    assert bloqueado.status_code == 409 and db.session.get(Jogo, classico.id)
    assert client.delete(f'/interface/api/jogos/{jogo_id}').status_code == 200
    assert db.session.get(Jogo, jogo_id) is None


def test_jogo_de_outro_bolao_e_protegido(client, gestao):
    preparar(client, gestao)
    _, boloes = gestao
    alheia = Rodada(nome='Rodada 1', campeonato=boloes[2].campeonato)
    jogo = Jogo(time_casa='X', time_fora='Y', rodada=alheia)
    db.session.add(jogo)
    db.session.commit()
    assert client.post(f'/interface/api/jogos/{jogo.id}/resultado', json={'golsCasa': 1, 'golsFora': 0}).status_code == 404
    assert client.delete(f'/interface/api/jogos/{jogo.id}').status_code == 404
    assert client.post('/interface/api/jogos', json={'casa': 'A', 'fora': 'B', 'rodadaId': alheia.id}).status_code == 404
    assert jogo.resultado is None


def test_classificacao_da_rodada(client, gestao):
    bolao, r1, classico, comum, ana = preparar(client, gestao)
    db.session.add(Resultado(jogo=classico, gols_casa_real=2, gols_fora_real=1))
    db.session.commit()
    dados = client.get(f'/interface/api/rodadas/{r1.id}/classificacao').get_json()
    assert dados['ranking'][0]['nome'] == 'Ana' and dados['ranking'][0]['pontos'] == 5


def test_classico_sugere_primeiro_gol_dos_palpites(client, gestao):
    bolao, r1, classico, comum, ana = preparar(client, gestao)
    bia = Participacao(bolao=bolao, nome_exibicao='Bia')
    db.session.add(bia)
    db.session.flush()
    db.session.add(Palpite(participacao=bia, jogo=classico, gols_casa=1, gols_fora=0, primeiro_gol='braithwaite '))
    db.session.commit()
    jogos = {j['id']: j for j in client.get('/interface/api/rodadas').get_json()['jogos']}
    assert jogos[classico.id]['sugestoesPrimeiroGol'] == [{'nome': 'Braithwaite', 'palpites': 2}]
    assert jogos[comum.id]['sugestoesPrimeiroGol'] == []
    # O nome digitado com outra grafia ainda pontua (comparação sem acento/maiúscula).
    client.post(f'/interface/api/jogos/{classico.id}/resultado', json={'golsCasa': 1, 'golsFora': 0, 'primeiroGol': 'BRAITHWAITE'})
    pontos = {i['participante'].nome: (i['pontos'], i['bonus_primeiro_gol']) for i in calcular_ranking(bolao)}
    assert pontos['Bia'] == (5 + 2, 2) and pontos['Ana'] == (3 + 2, 2)


def test_grade_da_rodada(client, gestao):
    bolao, r1, classico, comum, ana = preparar(client, gestao)
    db.session.add(Resultado(jogo=classico, gols_casa_real=2, gols_fora_real=1, primeiro_gol_real='Braithwaite'))
    db.session.commit()
    dados = client.get(f'/interface/api/rodadas/{r1.id}/grade').get_json()
    ana_dados = next(p for p in dados['participantes'] if p['nome'] == 'Ana')
    assert ana_dados['pontos'] == 7 and ana_dados['cravadas'] == 1
    celula = next(l for l in dados['linhas'] if l['jogo']['id'] == classico.id)['celulas'][str(ana.id)]
    assert celula['cravada'] and celula['pontos'] == 7 and celula['primeiroGol'] == 'Braithwaite'
    assert 'Ana' in dados['textoWhatsapp']
