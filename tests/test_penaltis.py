"""Palpite do placar dos pênaltis: pontuação, regras do bolão, lançamento e resultado manual."""
import json
from types import SimpleNamespace

import pytest

from database import db
from models import Bolao, Jogo, Palpite, PalpiteLog, Participacao, Resultado, Rodada
from services.grade_palpites import montar_grade
from services.historico_palpites import historico
from services.pontuacao import calcular_pontuacao
from services.ranking import calcular_ranking
from services.regras_pontuacao import REGRAS_PONTUACAO, validar_regras
from services.textos_whatsapp import texto_rodada
from tests.test_interface import entrar, gestao  # noqa: F401

REGRAS = dict(REGRAS_PONTUACAO)
BASE = {'comumExato': 3, 'comumResultado': 1, 'classicoExato': 5, 'classicoResultado': 3, 'primeiroGol': 2}


def palpite(casa, fora, pen=(None, None), situacao='valido'):
    return SimpleNamespace(gols_casa=casa, gols_fora=fora, penaltis_casa=pen[0], penaltis_fora=pen[1],
                           primeiro_gol=None, situacao=situacao)


def resultado(casa, fora, pen=(None, None)):
    return SimpleNamespace(gols_casa_real=casa, gols_fora_real=fora, penaltis_casa_real=pen[0], penaltis_fora_real=pen[1])


JOGO = SimpleNamespace(classico=False, primeiro_marcador=None, pode_penaltis=True)


# --- pontuação ---------------------------------------------------------------

def test_penaltis_exato_soma_ao_jogo():
    d = calcular_pontuacao(palpite(1, 1, (4, 3)), JOGO, resultado(1, 1, (4, 3)), REGRAS)
    assert (d.pontos_placar, d.pontos_penaltis, d.total) == (3, 3, 6)
    assert d.penaltis_exato and d.penaltis_vencedor and d.placar_exato


def test_penaltis_so_vencedor():
    d = calcular_pontuacao(palpite(0, 0, (5, 4)), JOGO, resultado(1, 1, (3, 2)), REGRAS)
    assert (d.pontos_placar, d.pontos_penaltis, d.total) == (1, 1, 2)
    assert not d.penaltis_exato and d.penaltis_vencedor
    errou = calcular_pontuacao(palpite(1, 1, (2, 3)), JOGO, resultado(1, 1, (3, 2)), REGRAS)
    assert errou.pontos_penaltis == 0 and not errou.penaltis_vencedor
    # Palpite de pênaltis empatado só valeria se fosse exato (o real nunca empata).
    assert calcular_pontuacao(palpite(1, 1, (3, 3)), JOGO, resultado(1, 1, (4, 3)), REGRAS).pontos_penaltis == 0


def test_regras_do_bolao_nos_penaltis():
    regras = {**REGRAS, 'penaltis_exato': 7, 'penaltis_vencedor': 4}
    assert calcular_pontuacao(palpite(1, 1, (4, 3)), JOGO, resultado(1, 1, (4, 3)), regras).pontos_penaltis == 7
    assert calcular_pontuacao(palpite(1, 1, (5, 3)), JOGO, resultado(1, 1, (4, 3)), regras).pontos_penaltis == 4


def test_sem_penaltis_reais_ou_sem_palpite_nao_pontua():
    sem_reais = calcular_pontuacao(palpite(2, 1, (4, 3)), JOGO, resultado(2, 1), REGRAS)
    assert (sem_reais.pontos_penaltis, sem_reais.total) == (0, 3)
    sem_palpite = calcular_pontuacao(palpite(1, 1), JOGO, resultado(1, 1, (4, 3)), REGRAS)
    assert (sem_palpite.pontos_penaltis, sem_palpite.total) == (0, 3)
    # Palpite não enviado não pontua nada, nem nos pênaltis.
    assert calcular_pontuacao(palpite(1, 1, (4, 3), 'nao_enviado'), JOGO, resultado(1, 1, (4, 3)), REGRAS).total == 0


def test_objetos_antigos_sem_atributos_de_penaltis():
    # Migrações antigas chamam com SimpleNamespace sem os campos de pênaltis.
    p = SimpleNamespace(gols_casa=1, gols_fora=0, primeiro_gol=None)
    r = SimpleNamespace(gols_casa_real=1, gols_fora_real=0)
    assert calcular_pontuacao(p, JOGO, r, REGRAS).total == 3


# --- regras ------------------------------------------------------------------

def test_validar_regras_penaltis_opcionais():
    base = {k: REGRAS[k] for k in ('comum_exato', 'comum_resultado', 'classico_exato', 'classico_resultado', 'primeiro_gol')}
    assert 'penaltis_exato' not in validar_regras(base)
    assert validar_regras({**base, 'penaltis_exato': 5, 'penaltis_vencedor': 2})['penaltis_exato'] == 5
    with pytest.raises(ValueError):
        validar_regras({**base, 'penaltis_exato': 1, 'penaltis_vencedor': 2})
    with pytest.raises(ValueError):
        validar_regras({**base, 'penaltis_exato': 100})
    # Só uma chave enviada: compara com o valor vigente da outra.
    with pytest.raises(ValueError):
        validar_regras({**base, 'penaltis_vencedor': 4}, {**REGRAS, 'penaltis_exato': 3})


def preparar(client, gestao):
    usuario, boloes = gestao
    bolao = boloes[0]
    r1 = Rodada(nome='Rodada 1', campeonato=bolao.campeonato)
    final = Jogo(time_casa='Santos', time_fora='Bahia', rodada=r1, pode_penaltis=True, ordem=1)
    comum = Jogo(time_casa='Grêmio', time_fora='Ceará', rodada=r1, ordem=2)
    ana = Participacao(bolao=bolao, nome_exibicao='Ana')
    db.session.add_all([r1, final, comum, ana])
    db.session.commit()
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': bolao.id})
    return bolao, r1, final, comum, ana


def test_api_regras_salva_e_mantem_penaltis(client, gestao):
    bolao, *_ = preparar(client, gestao)
    url = f'/interface/api/boloes/{bolao.id}/regras'
    r = client.put(url, json={**BASE, 'penaltisExato': 6, 'penaltisVencedor': 2})
    assert r.status_code == 200 and r.get_json()['regras']['penaltisExato'] == 6
    # Requisição antiga, sem os pênaltis: mantém os valores atuais.
    assert client.put(url, json={**BASE, 'comumExato': 4}).status_code == 200
    b = db.session.get(Bolao, bolao.id)
    assert (b.pontos_comum_exato, b.pontos_penaltis_exato, b.pontos_penaltis_vencedor) == (4, 6, 2)
    assert client.put(url, json={**BASE, 'penaltisExato': 1, 'penaltisVencedor': 2}).status_code == 400
    assert client.put(url, json={**BASE, 'penaltisVencedor': 7}).status_code == 400  # 6 vigente < 7
    assert client.put(url, json={**BASE, 'penaltisExato': 'x'}).status_code == 400
    classificacao = client.get(f'/interface/api/boloes/{bolao.id}/classificacao').get_json()
    assert classificacao['regras']['penaltisVencedor'] == 2


# --- lançamento ----------------------------------------------------------------

def salvar(client, rodada, pessoa, jogos):
    return client.post('/interface/api/palpites', json={'participacaoId': pessoa.id, 'rodadaId': rodada.id, 'jogos': jogos})


def test_lancamento_aceita_penaltis_e_registra_no_log(client, gestao):
    bolao, r1, final, comum, ana = preparar(client, gestao)
    resposta = salvar(client, r1, ana, {str(final.id): {'casa': '1', 'fora': '1', 'penaltisCasa': '4', 'penaltisFora': '3'},
                                        str(comum.id): {'casa': '2', 'fora': '0'}})
    assert resposta.status_code == 200, resposta.get_json()
    p = Palpite.query.filter_by(participacao_id=ana.id, jogo_id=final.id).one()
    assert (p.penaltis_casa, p.penaltis_fora) == (4, 3)
    novos = json.loads(PalpiteLog.query.filter_by(palpite_id=p.id).order_by(PalpiteLog.id.desc()).first().valores_novos)
    assert (novos['penaltis_casa'], novos['penaltis_fora']) == (4, 3)
    tela = client.get(f'/interface/api/palpites?rodada_id={r1.id}&participacao_id={ana.id}').get_json()
    jogo = next(j for j in tela['jogos'] if j['id'] == final.id)
    assert jogo['podePenaltis'] is True and (jogo['palpite']['penaltisCasa'], jogo['palpite']['penaltisFora']) == (4, 3)

    # Sem os campos: mantém; com os campos vazios: apaga (e registra a alteração).
    assert salvar(client, r1, ana, {str(final.id): {'casa': '2', 'fora': '2'}}).status_code == 200
    db.session.refresh(p)
    assert (p.gols_casa, p.penaltis_casa, p.penaltis_fora) == (2, 4, 3)
    assert salvar(client, r1, ana, {str(final.id): {'casa': '2', 'fora': '2', 'penaltisCasa': None,
                                                    'penaltisFora': None}}).status_code == 200
    db.session.refresh(p)
    assert (p.penaltis_casa, p.penaltis_fora) == (None, None)
    log = PalpiteLog.query.filter_by(palpite_id=p.id).order_by(PalpiteLog.id.desc()).first()
    assert json.loads(log.valores_anteriores)['penaltis_casa'] == 4
    itens = historico(ana, r1)
    assert any(m['antes'] == '2 × 2 (pên. 4 × 3)' and m['depois'] == '2 × 2' for i in itens for m in i['mudancas'])


@pytest.mark.parametrize('valores, mensagem', [
    ({'penaltisCasa': '4'}, 'Preencha os dois lados'),
    ({'penaltisCasa': '4', 'penaltisFora': 'x'}, 'pênaltis inteiros'),
    ({'penaltisCasa': '-1', 'penaltisFora': '3'}, 'pênaltis inteiros'),
    ({'penaltisCasa': '100', 'penaltisFora': '3'}, 'pênaltis inteiros'),
])
def test_lancamento_rejeita_penaltis_invalidos(client, gestao, valores, mensagem):
    bolao, r1, final, comum, ana = preparar(client, gestao)
    resposta = salvar(client, r1, ana, {str(final.id): {'casa': '1', 'fora': '1', **valores}})
    assert resposta.status_code == 422
    assert mensagem in resposta.get_json()['erros'][str(final.id)]
    assert Palpite.query.filter_by(participacao_id=ana.id).count() == 0


def test_lancamento_rejeita_penaltis_em_jogo_sem_disputa(client, gestao):
    bolao, r1, final, comum, ana = preparar(client, gestao)
    resposta = salvar(client, r1, ana, {str(comum.id): {'casa': '1', 'fora': '1', 'penaltisCasa': '4', 'penaltisFora': '3'}})
    assert resposta.status_code == 422
    assert resposta.get_json()['erros'][str(comum.id)] == 'Este jogo não tem disputa de pênaltis.'
    # Campos vazios em jogo sem pênaltis são ignorados.
    assert salvar(client, r1, ana, {str(comum.id): {'casa': '1', 'fora': '1', 'penaltisCasa': None,
                                                    'penaltisFora': None}}).status_code == 200


# --- resultado manual e exibição -------------------------------------------------

def test_resultado_manual_com_penaltis_e_pontuacao(client, gestao):
    bolao, r1, final, comum, ana = preparar(client, gestao)
    salvar(client, r1, ana, {str(final.id): {'casa': '1', 'fora': '1', 'penaltisCasa': '4', 'penaltisFora': '3'}})
    url = f'/interface/api/jogos/{final.id}/resultado'
    assert client.post(url, json={'golsCasa': 1, 'golsFora': 1, 'penaltisCasa': 4}).status_code == 400
    assert client.post(url, json={'golsCasa': 1, 'golsFora': 1, 'penaltisCasa': 3, 'penaltisFora': 3}).status_code == 400
    assert client.post(url, json={'golsCasa': 1, 'golsFora': 1, 'penaltisCasa': 4, 'penaltisFora': 3}).status_code == 200
    res = Resultado.query.filter_by(jogo_id=final.id).one()
    assert (res.penaltis_casa_real, res.penaltis_fora_real) == (4, 3)
    ana_ranking = next(i for i in calcular_ranking(bolao) if i['participante'].nome == 'Ana')
    assert ana_ranking['pontos'] == 3 + 3
    assert ana_ranking['cravadas'] == 1  # pênaltis não contam como cravada

    participantes, jogos, matriz, totais, bonus = montar_grade(bolao, r1)
    assert totais[ana.id]['pontos'] == 6
    texto = texto_rodada(bolao, r1, matriz, participantes, totais)
    assert 'Santos 1 × 1 Bahia* (pên. 4 × 3)' in texto and 'Ana: 1 × 1 (pên. 4 × 3) → 6 pts' in texto
    grade = client.get(f'/interface/api/rodadas/{r1.id}/grade').get_json()
    linha = next(l for l in grade['linhas'] if l['jogo']['id'] == final.id)
    assert (linha['jogo']['penaltisCasa'], linha['jogo']['penaltisFora']) == (4, 3)
    assert linha['celulas'][str(ana.id)]['pontosPenaltis'] == 3

    # Sem enviar os campos, o resultado mantém os pênaltis; com vazios, apaga.
    client.post(url, json={'golsCasa': 1, 'golsFora': 1})
    db.session.refresh(res)
    assert res.penaltis_casa_real == 4
    client.post(url, json={'golsCasa': 2, 'golsFora': 1, 'penaltisCasa': None, 'penaltisFora': ''})
    db.session.refresh(res)
    assert (res.penaltis_casa_real, res.penaltis_fora_real) == (None, None)


def test_resultado_com_penaltis_exige_jogo_que_pode_ter_penaltis(client, gestao):
    bolao, r1, final, comum, ana = preparar(client, gestao)
    resposta = client.post(f'/interface/api/jogos/{comum.id}/resultado',
                           json={'golsCasa': 1, 'golsFora': 1, 'penaltisCasa': 4, 'penaltisFora': 3})
    assert resposta.status_code == 400 and 'Pode ter pênaltis' in resposta.get_json()['erro']
    assert Resultado.query.filter_by(jogo_id=comum.id).count() == 0


def test_marcar_e_desmarcar_pode_ter_penaltis(client, gestao):
    bolao, r1, final, comum, ana = preparar(client, gestao)
    dados = {'casa': 'Grêmio', 'fora': 'Ceará', 'rodadaId': r1.id, 'data': '', 'classico': False}
    assert client.put(f'/interface/api/jogos/{comum.id}', json={**dados, 'podePenaltis': True}).status_code == 200
    assert db.session.get(Jogo, comum.id).pode_penaltis is True
    # Cliente antigo (sem o campo) não mexe na marcação.
    client.put(f'/interface/api/jogos/{comum.id}', json=dados)
    assert db.session.get(Jogo, comum.id).pode_penaltis is True
    client.post(f'/interface/api/jogos/{comum.id}/resultado',
                json={'golsCasa': 0, 'golsFora': 0, 'penaltisCasa': 5, 'penaltisFora': 4})
    client.put(f'/interface/api/jogos/{comum.id}', json={**dados, 'podePenaltis': False})
    jogo = db.session.get(Jogo, comum.id)
    assert jogo.pode_penaltis is False and jogo.resultado.penaltis_casa_real is None
    novo = client.post('/interface/api/jogos', json={**dados, 'casa': 'Vitória', 'fora': 'Sport', 'podePenaltis': True})
    assert db.session.get(Jogo, novo.get_json()['id']).pode_penaltis is True
    agenda = client.get(f'/interface/api/jogos?rodada_id={r1.id}').get_json()
    assert {j['casa']: j['podePenaltis'] for j in agenda['jogos']}['Vitória'] is True
