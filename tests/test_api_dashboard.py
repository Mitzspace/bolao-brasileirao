"""Dashboard da nova interface e serviço de classificação compartilhado."""
from database import db
from models import Jogo, Palpite, Participacao, Resultado, Rodada
from services.ranking import calcular_ranking, ranking_com_variacao
from tests.test_interface import entrar, gestao  # noqa: F401


def montar_rodadas(bolao):
    """Duas rodadas com resultado: Ana lidera a 1ª, Bia ultrapassa na 2ª."""
    ana = Participacao(bolao=bolao, nome_exibicao='Ana')
    bia = Participacao(bolao=bolao, nome_exibicao='Bia')
    r1 = Rodada(nome='Rodada 1', campeonato=bolao.campeonato)
    r2 = Rodada(nome='Rodada 2', campeonato=bolao.campeonato)
    r3 = Rodada(nome='Rodada 3', campeonato=bolao.campeonato)
    j1 = Jogo(time_casa='Casa 1', time_fora='Fora 1', rodada=r1)
    j2 = Jogo(time_casa='Casa 2', time_fora='Fora 2', rodada=r2, classico=True)
    j3 = Jogo(time_casa='Casa 3', time_fora='Fora 3', rodada=r3)
    j4 = Jogo(time_casa='Casa 4', time_fora='Fora 4', rodada=r3)
    db.session.add_all([ana, bia, j1, j2, j3, j4])
    db.session.flush()
    db.session.add_all([
        Resultado(jogo=j1, gols_casa_real=2, gols_fora_real=1),
        Resultado(jogo=j2, gols_casa_real=0, gols_fora_real=0),
        Palpite(participacao=ana, jogo=j1, gols_casa=2, gols_fora=1),  # exato comum: 3
        Palpite(participacao=bia, jogo=j1, gols_casa=1, gols_fora=0),  # resultado: 1
        Palpite(participacao=ana, jogo=j2, gols_casa=1, gols_fora=0),  # erro: 0
        Palpite(participacao=bia, jogo=j2, gols_casa=0, gols_fora=0),  # exato clássico: 5
        Palpite(participacao=ana, jogo=j3, gols_casa=1, gols_fora=1),  # rodada 3 sem resultado
    ])
    db.session.commit()
    return ana, bia, r1, r2, r3


def test_dashboard_exige_login_e_bolao(client, gestao):
    usuario, boloes = gestao
    assert client.get('/interface/api/dashboard').status_code == 401
    entrar(client, usuario)
    resposta = client.get('/interface/api/dashboard')
    assert resposta.status_code == 409 and resposta.is_json  # dois bolões, nenhum escolhido


def test_dashboard_com_dados_reais(client, gestao):
    usuario, boloes = gestao
    ana, bia, r1, r2, r3 = montar_rodadas(boloes[0])
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': boloes[0].id})
    dados = client.get('/interface/api/dashboard').get_json()

    assert dados['bolao']['id'] == boloes[0].id
    assert dados['participantesAtivos'] == 3  # responsável + Ana + Bia
    assert dados['rodada']['id'] == r3.id and dados['rodada']['numero'] == 3
    assert [j['status'] for j in dados['jogos']] == ['agendado', 'agendado']
    assert dados['jogosEncerrados'] == 0
    # Rodada 3 tem 2 jogos para 3 participantes; Ana já mandou 1.
    assert dados['palpitesFaltantes'] == 5

    top = {i['nome']: i for i in dados['top5']}
    assert (top['Bia']['pontos'], top['Bia']['posicao'], top['Bia']['variacao']) == (6, 1, 1)
    assert (top['Ana']['pontos'], top['Ana']['posicao'], top['Ana']['variacao']) == (3, 2, -1)
    assert dados['variacaoReferencia'] == 'Rodada 2'
    assert 'pagamento' not in str(dados).lower() and 'valor' not in str(dados).lower()


def test_dashboard_de_outro_bolao_nao_vaza(client, gestao):
    usuario, boloes = gestao
    montar_rodadas(boloes[2])  # bolão de outro responsável
    entrar(client, usuario)
    assert client.post('/interface/selecionar', data={'bolao_id': boloes[2].id}).status_code == 403
    client.post('/interface/selecionar', data={'bolao_id': boloes[0].id})
    nomes = [i['nome'] for i in client.get('/interface/api/dashboard').get_json()['top5']]
    assert 'Ana' not in nomes and 'Bia' not in nomes


def test_ranking_acumulado_ate_rodada(app, gestao):
    _, boloes = gestao
    ana, bia, r1, r2, r3 = montar_rodadas(boloes[0])
    ate_r1 = calcular_ranking(boloes[0], ate_rodada=r1)
    assert [i['participante'].nome for i in ate_r1[:2]] == ['Ana', 'Bia']
    geral = calcular_ranking(boloes[0])
    assert [i['participante'].nome for i in geral[:2]] == ['Bia', 'Ana']
    so_r2 = calcular_ranking(boloes[0], rodada=r2)
    assert {i['participante'].nome: i['pontos'] for i in so_r2}['Bia'] == 5
    ranking, ultima = ranking_com_variacao(boloes[0])
    assert ultima.id == r2.id and ranking[0]['variacao'] == 1


def test_rodada_atual_ignora_jogo_adiado_de_rodada_antiga(app, campeonato_teste):
    from services.resumo_boloes import rodadas_de_referencia
    r1, r2, r3 = (Rodada(nome=f'Rodada {n}', campeonato=campeonato_teste) for n in (1, 2, 3))
    adiado = Jogo(time_casa='A', time_fora='B', rodada=r1)       # rodada 1 com jogo adiado
    feito1 = Jogo(time_casa='C', time_fora='D', rodada=r1)
    feito2 = Jogo(time_casa='E', time_fora='F', rodada=r2)       # rodada 2 completa
    proximo = Jogo(time_casa='G', time_fora='H', rodada=r3)      # rodada 3 a jogar
    db.session.add_all([adiado, feito1, feito2, proximo])
    db.session.flush()
    db.session.add_all([Resultado(jogo=feito1, gols_casa_real=1, gols_fora_real=0),
                        Resultado(jogo=feito2, gols_casa_real=2, gols_fora_real=2)])
    db.session.commit()
    assert rodadas_de_referencia({campeonato_teste.id})[campeonato_teste.id]['rodada'].id == r3.id
    db.session.add(Resultado(jogo=proximo, gols_casa_real=0, gols_fora_real=0))
    db.session.commit()
    ref = rodadas_de_referencia({campeonato_teste.id})[campeonato_teste.id]
    assert ref['rodada'].id == r3.id and ref['ultima']
