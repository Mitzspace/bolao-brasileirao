from datetime import datetime
import json
import pytest
from database import db
from models import Jogo, Palpite, PalpiteLog
from tests.test_acesso_gestao import gestao, sessao


@pytest.fixture
def lote(gestao):
    app, usuarios, bolao, pessoa, rodada, jogo = gestao
    outro = Jogo(time_casa='Casa 2', time_fora='Fora 2', rodada_id=rodada, data=datetime(2020, 1, 1))
    db.session.add(outro)
    db.session.commit()
    client = app.test_client()
    sessao(client, usuarios['responsavel'])
    return client, f'/b/{bolao}/palpites', {'participante_id': pessoa, 'rodada_id': rodada}, jogo, outro.id


@pytest.mark.parametrize('valor', ['-1', '1.5', 'abc', '1e2', '2147483648'])
def test_erro_preserva_lote_sem_gravacao(lote, valor):
    client, url, dados, a, b = lote
    dados.update({f'casa_{a}': '12', f'fora_{a}': '10', f'casa_{b}': valor, f'fora_{b}': '2'})
    resposta = client.post(url, data=dados)
    assert resposta.status_code == 422
    assert 'value="12"' in resposta.text and f'value="{valor}"' in resposta.text
    assert 'Nada foi salvo' in resposta.text
    assert Palpite.query.count() == PalpiteLog.query.count() == 0


def test_lote_dois_digitos_tardio_recebimento_e_auditoria(lote):
    client, url, dados, a, b = lote
    dados.update({f'casa_{a}': '12', f'fora_{a}': '10', f'casa_{b}': '2', f'fora_{b}': '1', 'recebido_em':'2026-10-11T12:30'})
    assert client.post(url, data=dados).status_code == 302
    assert Palpite.query.count() == PalpiteLog.query.count() == 2
    palpite = Palpite.query.filter_by(jogo_id=b).one()
    assert palpite.lancado_apos_inicio and palpite.recebido_em == datetime(2026, 10, 11, 15, 30)
    assert palpite.origem == 'responsavel' and palpite.lancado_por
    dados[f'casa_{b}'] = '3'
    dados.pop('recebido_em')
    assert client.post(url, data=dados).status_code == 302
    log = PalpiteLog.query.order_by(PalpiteLog.id.desc()).first()
    assert json.loads(log.valores_anteriores)['gols_casa'] == 2
    assert json.loads(log.valores_novos)['gols_casa'] == 3
    assert palpite.recebido_em == datetime(2026, 10, 11, 15, 30)


def test_par_incompleto_e_data_invalida(lote):
    client, url, dados, a, b = lote
    dados.update({f'casa_{a}':'1', 'recebido_em':'data inválida'})
    resposta = client.post(url, data=dados)
    assert resposta.status_code == 422 and 'Preencha os dois' in resposta.text
    assert 'data e hora válidas' in resposta.text
    assert Palpite.query.count() == 0


def test_guardado_nao_impede_outros_jogos_e_nao_pode_ser_sobrescrito(lote):
    client, url, dados, a, b = lote
    dados.update({f'casa_{a}':'1', f'fora_{a}':'0'})
    assert client.post(url, data=dados).status_code == 302
    palpite = Palpite.query.one()
    palpite.excluido_por_desistencia = True
    db.session.commit()
    assert client.post(url, data=dados).status_code == 422
    dados.pop(f'casa_{a}')
    dados.pop(f'fora_{a}')
    dados.update({f'casa_{b}':'2', f'fora_{b}':'1'})
    assert client.post(url, data=dados).status_code == 302
    assert palpite.excluido_por_desistencia and palpite.gols_casa == 1
    assert Palpite.query.count() == 2


def test_formulario_acessivel_e_campos_existentes(lote):
    client, url, dados, a, b = lote
    resposta = client.get(url, query_string=dados)
    assert resposta.status_code == 200
    assert resposta.text.count('inputmode="numeric"') == 4
    assert 'avanco-automatico' in resposta.text
    assert 'Iniciado — lançamento permitido' in resposta.text
    assert 'name="casa_' in resposta.text and 'lancamento-rapido.js' in resposta.text
