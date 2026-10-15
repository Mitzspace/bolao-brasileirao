from flask import g
from database import db
from models import Bolao, Campeonato, Jogo, Palpite, Participacao, Resultado, Rodada
from services.resumo_boloes import resumos_boloes, rodadas_de_referencia
from tests.apoio import estrutura, login
from tests.test_interface import dados_renderizados
from utils import hash_senha


def test_contagens_independentes_e_participacoes_inativas(app, participante_teste, campeonato_teste):
    a, pa = estrutura(participante_teste, campeonato_teste, 'Mesmo nome')
    b, pb = estrutura(participante_teste, campeonato_teste, 'Mesmo nome')
    sem_conta = Participacao(bolao=a, nome_exibicao='Sem conta')
    removido = Participacao(bolao=a, nome_exibicao='Removido', status='removido')
    r = Rodada(nome='Rodada 2', campeonato=campeonato_teste)
    j1 = Jogo(time_casa='A', time_fora='B', rodada=r)
    j2 = Jogo(time_casa='C', time_fora='D', rodada=r)
    db.session.add_all([sem_conta, removido, j1, j2])
    db.session.flush()
    db.session.add_all([Palpite(participacao=sem_conta, jogo=j1, gols_casa=0, gols_fora=0),
                        Palpite(participacao=removido, jogo=j2, gols_casa=1, gols_fora=0)])
    db.session.commit()
    resumos = resumos_boloes([a, b])
    assert (resumos[a.id]['ativos'], resumos[a.id]['pendencias']) == (2, 3)
    assert (resumos[b.id]['ativos'], resumos[b.id]['pendencias']) == (1, 2)
    assert sem_conta.usuario_id is None


def test_referencia_numerica_resultados_e_campeonatos(app, campeonato_teste):
    outro = Campeonato(nome='Outro', ano=2027)
    r10 = Rodada(nome='Rodada 10', campeonato=campeonato_teste)
    r2 = Rodada(nome='Rodada 2', campeonato=campeonato_teste)
    r1 = Rodada(nome='Rodada 1', campeonato=campeonato_teste)
    vazio = Rodada(nome='Rodada 0', campeonato=campeonato_teste)
    jogos = [Jogo(time_casa='A', time_fora='B', rodada=r) for r in [r10, r2, r1]]
    db.session.add_all([outro, vazio, *jogos])
    db.session.flush()
    db.session.add(Resultado(jogo=jogos[2], gols_casa_real=1, gols_fora_real=0))
    db.session.commit()
    ref = rodadas_de_referencia({campeonato_teste.id, outro.id})
    assert ref[campeonato_teste.id]['rodada'].id == r2.id
    assert ref[outro.id]['rodada'] is None
    r2.aberta = False
    db.session.commit()
    assert rodadas_de_referencia({campeonato_teste.id})[campeonato_teste.id]['rodada'].id == r10.id
    for jogo in jogos:
        jogo.encerrado = True
    db.session.commit()
    ref = rodadas_de_referencia({campeonato_teste.id})[campeonato_teste.id]
    assert ref['ultima'] and ref['rodada'].id == r10.id


def test_meus_boloes_login_e_memoria(app, client, participante_teste, campeonato_teste):
    a, pa = estrutura(participante_teste, campeonato_teste, 'Gerenciado A')
    b, pb = estrutura(participante_teste, campeonato_teste, 'Gerenciado B')
    excluido, pe = estrutura(participante_teste, campeonato_teste, 'Somente participante')
    pe.papel = 'participante'
    participante_teste.senha = hash_senha('senha123')
    db.session.commit()
    login(client, participante_teste)
    with dados_renderizados(app) as dados:
        client.get('/interface/')
    assert {x['id'] for x in dados[0]['boloes']} == {a.id, b.id}  # só onde é responsável
    assert dados[0]['bolaoAtualId'] is None  # vários: precisa escolher
    client.post('/interface/selecionar', data={'bolao_id': b.id})
    client.get('/logout')
    g.pop('_login_user', None)
    client.post('/login', data={'email': participante_teste.email, 'senha': 'senha123'})
    with dados_renderizados(app) as dados:
        client.get('/interface/')
    assert dados[0]['bolaoAtualId'] == b.id  # lembra o último bolão no novo login


def test_um_bolao_seleciona_automaticamente(app, client, participante_teste, campeonato_teste):
    b, p = estrutura(participante_teste, campeonato_teste, 'Único')
    participante_teste.senha = hash_senha('senha123')
    db.session.commit()
    resposta = client.post('/login', data={'email': participante_teste.email, 'senha': 'senha123'})
    assert resposta.location.endswith('/interface/')
    with dados_renderizados(app) as dados:
        client.get('/interface/')
    assert dados[0]['bolaoAtualId'] == b.id
