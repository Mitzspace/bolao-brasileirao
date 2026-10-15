from datetime import datetime, timedelta
import pytest
from database import db
from models import Bolao, BonusRodada, Campeonato, Jogo, Participacao, Palpite, Resultado, Rodada
from tests.test_acesso_gestao import gestao, sessao


def texto(response):
    assert response.status_code == 200
    return response.get_json()['textoWhatsapp']


def ranking(client, bolao, rodada=None):
    return texto(client.get(f'/interface/api/boloes/{bolao}/classificacao' + (f'?rodada_id={rodada}' if rodada else '')))


def preparar(gestao):
    client = gestao[0].test_client()
    sessao(client, gestao[1]['responsavel'])
    jogo = db.session.get(Jogo, gestao[5])
    pessoa = db.session.get(Participacao, gestao[3])
    jogo.classico = True
    jogo.data = datetime.now() - timedelta(days=1)
    db.session.add(Resultado(jogo=jogo, gols_casa_real=2, gols_fora_real=1, primeiro_gol_real='João'))
    db.session.add(Palpite(participacao=pessoa, jogo=jogo, gols_casa=2, gols_fora=1, primeiro_gol='joao'))
    db.session.add(BonusRodada(participacao=pessoa, participante_id=gestao[1]['comum'], rodada_id=gestao[4], pontos=3))
    outra = Rodada(nome='Rodada 2', campeonato=jogo.rodada.campeonato)
    futuro = Jogo(time_casa='C', time_fora='D', rodada=jogo.rodada, data=datetime.now()+timedelta(days=1))
    segundo = Jogo(time_casa='E', time_fora='F', rodada=outra)
    db.session.add_all([futuro, segundo])
    db.session.flush()
    db.session.add(Palpite(participacao=pessoa, jogo=futuro, gols_casa=9, gols_fora=8, primeiro_gol='Segredo futuro'))
    db.session.add(Resultado(jogo=segundo, gols_casa_real=0, gols_fora_real=0))
    db.session.add(Palpite(participacao=pessoa, jogo=segundo, gols_casa=0, gols_fora=0))
    db.session.commit()
    return client, jogo, pessoa, outra


def test_ranking_geral_rodada_bonus_sem_duplicacao(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    geral = ranking(client, gestao[2])
    rodada = ranking(client, gestao[2], gestao[4])
    segunda = ranking(client, gestao[2], outra.id)
    assert '🟩 1. Sem conta – 13 pontos' in geral          # 5 + 2 (1º gol) + 3 (créditos) + 3 (rodada 2)
    assert '🟩 1. Sem conta – 10 pontos' in rodada
    assert '🟩 1. Sem conta – 3 pontos' in segunda
    assert geral.startswith('*🏆Bolão*') and rodada.startswith('*🏆Bolão · Rodada 1*')
    assert '@teste.com' not in geral


def test_resumo_oculta_palpites_sem_resultado_e_confere_totais(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    resumo = texto(client.get(f'/interface/api/rodadas/{gestao[4]}/grade'))
    assert 'A 2 × 1 B' in resumo and 'clássico' in resumo
    assert 'Primeiro gol: João' in resumo
    assert 'Sem conta: 2 × 1 · 1º gol: joao → 7 pts' in resumo
    assert 'Sem conta: 10 pts (créditos históricos: 3' in resumo
    assert 'sem palpite' in resumo and 'aguardando resultado' in resumo
    assert 'Segredo futuro' not in resumo and '9 × 8' not in resumo
    assert '@teste.com' not in resumo


def test_textos_isolados_e_rodada_invalida(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    origem = db.session.get(Bolao, gestao[2])
    b = Bolao(nome='Segundo', campeonato=origem.campeonato, criador=origem.criador)
    db.session.add(Participacao(bolao=b, usuario=origem.criador, nome_exibicao='Outro gestor', papel='responsavel'))
    camp = Campeonato(nome='Privado', ano=2027)
    r = Rodada(nome='Rodada privada', campeonato=camp)
    db.session.add(r)
    db.session.commit()
    t = ranking(client, b.id)
    assert 'Sem conta' not in t and 'Outro gestor – 0 pontos' in t
    for parametro in [str(r.id), 'abc']:
        assert client.get(f'/interface/api/boloes/{origem.id}/classificacao?rodada_id={parametro}').status_code == 404


def test_texto_exige_responsavel(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    sessao(client, gestao[1]['comum'])
    assert client.get(f'/interface/api/boloes/{gestao[2]}/classificacao').status_code == 403
    assert client.get(f'/interface/api/rodadas/{gestao[4]}/grade').status_code == 403


def test_resultado_corrigido_atualiza_texto(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    assert 'Sem conta – 10 pontos' in ranking(client, gestao[2], gestao[4])
    jogo.resultado.gols_casa_real = 0
    jogo.resultado.gols_fora_real = 0
    db.session.commit()
    assert 'Sem conta – 3 pontos' in ranking(client, gestao[2], gestao[4])
