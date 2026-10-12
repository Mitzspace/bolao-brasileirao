from datetime import datetime, timedelta
from html import unescape
import re
import pytest
from database import db
from models import Bolao, BonusRodada, Campeonato, Jogo, Participacao, Palpite, Resultado, Rodada
from tests.test_acesso_gestao import gestao, sessao


def texto(response):
    assert response.status_code == 200
    return unescape(re.search(r'<textarea[^>]*data-texto-copia[^>]*>(.*?)</textarea>', response.text, re.S).group(1))


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
    url = f'/b/{gestao[2]}/ranking'
    geral = texto(client.get(url))
    rodada = texto(client.get(url + f'?rodada_id={gestao[4]}'))
    segunda = texto(client.get(url + f'?rodada_id={outra.id}'))
    assert '1º · Sem conta · 13 pts (bônus 1º gol: 2; créditos históricos: 3)' in geral
    assert '1º · Sem conta · 10 pts' in rodada
    assert '1º · Sem conta · 3 pts (bônus 1º gol: 0; créditos históricos: 0)' in segunda
    assert 'Ranking geral' in geral and 'Ranking · Rodada 1' in rodada
    assert '@teste.com' not in geral
    assert 'já estão incluídos' in geral


def test_resumo_oculta_palpites_sem_resultado_e_confere_totais(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    resumo = texto(client.get(f'/b/{gestao[2]}/rodada/{gestao[4]}/palpites'))
    assert 'A 2 × 1 B' in resumo and 'clássico' in resumo
    assert 'Primeiro gol: João' in resumo
    assert 'Sem conta: 2 × 1 · 1º gol: joao → 7 pts' in resumo
    assert 'Sem conta: 10 pts (créditos históricos: 3' in resumo
    assert 'sem palpite' in resumo and 'aguardando resultado' in resumo
    assert 'Segredo futuro' not in resumo and '9 × 8' not in resumo
    assert '@teste.com' not in resumo


def test_textos_isolados_e_rodada_invalida(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    origem = db.session.get(Bolao,gestao[2])
    b=Bolao(nome='Segundo',campeonato=origem.campeonato,criador=origem.criador)
    db.session.add(Participacao(bolao=b,usuario=origem.criador,nome_exibicao='Outro gestor',papel='responsavel'))
    camp=Campeonato(nome='Privado',ano=2027)
    r=Rodada(nome='Rodada privada',campeonato=camp)
    db.session.add(r); db.session.commit()
    t=texto(client.get(f'/b/{b.id}/ranking'))
    assert 'Sem conta' not in t and 'Outro gestor · 0 pts' in t
    for parametro in [str(r.id), 'abc', f'{gestao[4]}&rodada_id={outra.id}']:
        assert client.get(f'/b/{origem.id}/ranking?rodada_id={parametro}').status_code==404
    troca=client.post('/boloes/selecionar',data={'bolao_id':b.id,'bolao_origem_id':origem.id,'aba_origem':'participante.ranking','rodada_origem_id':gestao[4]})
    assert troca.location==f'/b/{b.id}/ranking?rodada_id={gestao[4]}'


def test_preview_escapado_e_acesso_restrito(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    pessoa.nome_exibicao='</textarea><script>alert(1)</script>'
    db.session.commit()
    response=client.get(f'/b/{gestao[2]}/ranking')
    assert '&lt;/textarea&gt;&lt;script&gt;' in response.text
    assert 'copiar-texto.js' in response.text and 'aria-live="polite"' in response.text
    sessao(client,gestao[1]['comum'])
    assert client.get(f'/b/{gestao[2]}/ranking').status_code==403
    gestao[0].config['FEATURE_PARTICIPANTE_LOGIN']=True
    response=client.get(f'/ranking?bolao_id={gestao[2]}')
    assert response.status_code==200 and 'data-texto-copia' not in response.text


def test_resultado_corrigido_atualiza_texto(gestao):
    client, jogo, pessoa, outra = preparar(gestao)
    url=f'/b/{gestao[2]}/ranking?rodada_id={gestao[4]}'
    assert 'Sem conta · 10 pts' in texto(client.get(url))
    jogo.resultado.gols_casa_real=0
    jogo.resultado.gols_fora_real=0
    db.session.commit()
    assert 'Sem conta · 3 pts' in texto(client.get(url))
