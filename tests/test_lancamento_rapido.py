"""Lançamento em lote pela API: validação de todos os campos antes de gravar e auditoria."""
from datetime import datetime
import json
import pytest
from database import db
from models import Jogo, Palpite, PalpiteLog
from tests.apoio_lancamento import enviar, texto_erros
from tests.test_acesso_gestao import gestao, sessao  # noqa: F401


@pytest.fixture
def lote(gestao):
    app, usuarios, bolao, pessoa, rodada, jogo = gestao
    outro = Jogo(time_casa='Casa 2', time_fora='Fora 2', rodada_id=rodada, data=datetime(2020, 1, 1))
    db.session.add(outro)
    db.session.commit()
    client = app.test_client()
    sessao(client, usuarios['responsavel'])
    return client, None, {'participante_id': pessoa, 'rodada_id': rodada}, jogo, outro.id


@pytest.mark.parametrize('valor', ['-1', '1.5', 'abc', '1e2', '2147483648'])
def test_erro_preserva_lote_sem_gravacao(lote, valor):
    client, _, dados, a, b = lote
    dados.update({f'casa_{a}': '12', f'fora_{a}': '10', f'casa_{b}': valor, f'fora_{b}': '2'})
    resposta = enviar(client, dados)
    assert resposta.status_code == 422
    assert 'Nada foi salvo' in resposta.get_json()['erro'] and str(b) in resposta.get_json()['erros']
    assert Palpite.query.count() == PalpiteLog.query.count() == 0


def test_lote_dois_digitos_tardio_recebimento_e_auditoria(lote):
    client, _, dados, a, b = lote
    # "recebido_em" não é mais gravado (saiu da tela); a data/hora fica no log.
    dados.update({f'casa_{a}': '12', f'fora_{a}': '10', f'casa_{b}': '2', f'fora_{b}': '1', 'recebido_em': '2026-10-11T12:30'})
    assert enviar(client, dados).status_code == 200
    assert Palpite.query.count() == PalpiteLog.query.count() == 2
    palpite = Palpite.query.filter_by(jogo_id=b).one()
    assert palpite.lancado_apos_inicio and palpite.recebido_em is None
    assert palpite.origem == 'responsavel' and palpite.lancado_por
    dados[f'casa_{b}'] = '3'
    dados.pop('recebido_em')
    assert enviar(client, dados).status_code == 200
    log = PalpiteLog.query.order_by(PalpiteLog.id.desc()).first()
    assert json.loads(log.valores_anteriores)['gols_casa'] == 2
    assert json.loads(log.valores_novos)['gols_casa'] == 3
    assert json.loads(log.valores_novos)['canal'] == 'painel' and log.alterado_por


def test_par_incompleto_e_data_invalida(lote):
    client, _, dados, a, b = lote
    dados.update({f'casa_{a}': '1', 'recebido_em': 'data inválida'})  # ignorado: o campo saiu da tela
    resposta = enviar(client, dados)
    assert resposta.status_code == 422
    assert 'Preencha os dois' in texto_erros(resposta) and 'data e hora' not in texto_erros(resposta)
    assert Palpite.query.count() == 0


def test_guardado_nao_impede_outros_jogos_e_nao_pode_ser_sobrescrito(lote):
    client, _, dados, a, b = lote
    dados.update({f'casa_{a}': '1', f'fora_{a}': '0'})
    assert enviar(client, dados).status_code == 200
    palpite = Palpite.query.one()
    palpite.excluido_por_desistencia = True
    db.session.commit()
    assert enviar(client, dados).status_code == 422
    dados.pop(f'casa_{a}')
    dados.pop(f'fora_{a}')
    dados.update({f'casa_{b}': '2', f'fora_{b}': '1'})
    assert enviar(client, dados).status_code == 200
    assert palpite.excluido_por_desistencia and palpite.gols_casa == 1
    assert Palpite.query.count() == 2


def test_tela_informa_jogos_iniciados(lote):
    client, _, dados, a, b = lote
    tela = client.get(f"/interface/api/palpites?rodada_id={dados['rodada_id']}&participacao_id={dados['participante_id']}").get_json()
    jogos = {j['id']: j for j in tela['jogos']}
    assert jogos[b]['iniciado'] is True and jogos[a]['iniciado'] is False  # lançamento tardio continua permitido
