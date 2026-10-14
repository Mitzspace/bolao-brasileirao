"""Lançamento de palpites pela API: mesmas regras e mesmo resultado da tela atual."""
import json
from datetime import datetime, timedelta

from database import db
from models import Jogo, Palpite, PalpiteLog, Participacao, Rodada
from tests.test_interface import entrar, gestao  # noqa: F401


def preparar(client, gestao):
    usuario, boloes = gestao
    bolao = boloes[0]
    r1 = Rodada(nome='Rodada 1', campeonato=bolao.campeonato)
    r2 = Rodada(nome='Rodada 2', campeonato=bolao.campeonato)
    db.session.add_all([r1, r2])
    db.session.flush()
    j1 = Jogo(time_casa='Flamengo', time_fora='Vasco', rodada=r1, classico=True)
    j2 = Jogo(time_casa='Santos', time_fora='Bahia', rodada=r1, data=datetime.now() - timedelta(hours=1))
    ana = Participacao(bolao=bolao, nome_exibicao='Ana')
    bia = Participacao(bolao=bolao, nome_exibicao='Bia')
    tardio = Participacao(bolao=bolao, nome_exibicao='Tardio', rodada_entrada=r2)
    db.session.add_all([j1, j2, ana, bia, tardio, r2])
    db.session.flush()
    db.session.add(Palpite(participacao=ana, jogo=j1, gols_casa=1, gols_fora=0))
    db.session.commit()
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': bolao.id})
    return bolao, r1, r2, j1, j2, ana, bia, tardio


def test_tela_abre_no_primeiro_pendente_e_mostra_palpites(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    dados = client.get(f'/interface/api/palpites?rodada_id={r1.id}').get_json()
    nomes = [p['nome'] for p in dados['participantes']]
    assert 'Tardio' not in nomes  # entra só na rodada 2
    assert dados['pessoa']['nome'] == 'Ana'  # Ana tem 1 de 2: ainda pendente
    assert [j['numero'] for j in dados['jogos']] == [1, 2]
    assert dados['jogos'][0]['palpite'] == {'casa': 1, 'fora': 0, 'primeiroGol': '', 'situacao': 'valido',
                                            'guardado': False, 'pontos': None}
    assert dados['jogos'][1]['iniciado'] is True and dados['jogos'][1]['palpite'] is None
    outra = client.get(f'/interface/api/palpites?rodada_id={r1.id}&participacao_id={bia.id}').get_json()
    assert outra['pessoa']['nome'] == 'Bia'
    assert client.get(f'/interface/api/palpites?rodada_id={r1.id}&participacao_id={tardio.id}').status_code == 409


def test_salvar_e_ir_para_o_proximo(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    resposta = client.post('/interface/api/palpites', json={
        'participacaoId': ana.id, 'rodadaId': r1.id, 'acao': 'proximo', 'recebidoEm': '2026-10-17T20:00',
        'jogos': {str(j1.id): {'casa': '2', 'fora': '1', 'primeiroGol': 'Pedro', 'situacao': 'valido'},
                  str(j2.id): {'casa': '0', 'fora': '0', 'primeiroGol': 'Ignorado', 'situacao': 'valido'}}})
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados['proximoId'] == bia.id and '2 palpites' in dados['mensagem']
    p1 = Palpite.query.filter_by(participacao_id=ana.id, jogo_id=j1.id).one()
    p2 = Palpite.query.filter_by(participacao_id=ana.id, jogo_id=j2.id).one()
    assert (p1.gols_casa, p1.gols_fora, p1.primeiro_gol, p1.origem) == (2, 1, 'Pedro', 'responsavel')
    assert p2.primeiro_gol is None  # primeiro gol só em clássico
    assert p1.recebido_em == datetime(2026, 10, 17, 23, 0)  # 20h em São Paulo = 23h UTC
    assert p2.lancado_apos_inicio is True
    assert PalpiteLog.query.count() == 3  # criação inicial + 1 edição + 1 criação, todas auditadas


def test_erro_nao_grava_nada(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    resposta = client.post('/interface/api/palpites', json={
        'participacaoId': bia.id, 'rodadaId': r1.id,
        'jogos': {str(j1.id): {'casa': '1', 'fora': '1'}, str(j2.id): {'casa': '3'}}})
    assert resposta.status_code == 422
    assert resposta.get_json()['erros'] == {str(j2.id): 'Preencha os dois placares deste jogo.'}
    assert Palpite.query.filter_by(participacao_id=bia.id).count() == 0


def test_nao_enviou_rodada_e_situacao(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    client.post('/interface/api/palpites', json={'participacaoId': bia.id, 'rodadaId': r1.id, 'naoEnviouRodada': True})
    assert {p.situacao for p in Palpite.query.filter_by(participacao_id=bia.id)} == {'nao_enviado'}
    client.post('/interface/api/palpites', json={'participacaoId': ana.id, 'rodadaId': r1.id,
                'jogos': {str(j2.id): {'situacao': 'fora_prazo'}}})
    assert Palpite.query.filter_by(participacao_id=ana.id, jogo_id=j2.id).one().situacao == 'fora_prazo'


def test_previa_whatsapp_e_texto_no_historico(client, gestao):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    texto = 'Flamengo 3x0 Vasco ★ Gabigol\nSantos 1x1 Bahia'
    previa = client.post('/interface/api/palpites/previa-whatsapp', json={'participacaoId': bia.id, 'rodadaId': r1.id, 'texto': texto})
    assert previa.status_code == 200
    dados = previa.get_json()
    assert [l['jogo_id'] for l in dados['linhas']] == [j1.id, j2.id] and dados['linhas'][0]['primeiro_gol'] == 'Gabigol'
    assert Palpite.query.filter_by(participacao_id=bia.id).count() == 0  # prévia não grava
    salvar = client.post('/interface/api/palpites', json={
        'participacaoId': bia.id, 'rodadaId': r1.id, 'whatsappToken': dados['token'], 'whatsappJogos': f'{j1.id},{j2.id}',
        'jogos': {str(j1.id): {'casa': '3', 'fora': '0', 'primeiroGol': 'Gabigol'}, str(j2.id): {'casa': '1', 'fora': '1'}}})
    assert salvar.status_code == 200
    logs = PalpiteLog.query.join(Palpite).filter(Palpite.participacao_id == bia.id).all()
    assert all(json.loads(l.valores_novos)['texto_original_whatsapp'] == texto for l in logs)
    # Token de outra pessoa é recusado.
    outro = client.post('/interface/api/palpites', json={'participacaoId': ana.id, 'rodadaId': r1.id,
            'whatsappToken': dados['token'], 'whatsappJogos': str(j1.id), 'jogos': {str(j1.id): {'casa': '1', 'fora': '1'}}})
    assert outro.status_code == 422 and 'whatsapp' in outro.get_json()['erros']


def test_isolamento_e_csrf(client, gestao, app):
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    _, boloes = gestao
    alheia = Participacao(bolao=boloes[2], nome_exibicao='Alheia')
    db.session.add(alheia)
    db.session.commit()
    assert client.post('/interface/api/palpites', json={'participacaoId': alheia.id, 'rodadaId': r1.id}).status_code == 404
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/interface/api/palpites', json={'participacaoId': ana.id, 'rodadaId': r1.id}).status_code == 403


def test_mesmo_resultado_da_tela_antiga(client, gestao):
    """O mesmo lote enviado pela tela atual e pela API produz os mesmos palpites."""
    bolao, r1, r2, j1, j2, ana, bia, tardio = preparar(client, gestao)
    client.post(f'/b/{bolao.id}/palpites', data={'participante_id': ana.id, 'rodada_id': r1.id, 'acao': 'ficar',
                f'casa_{j1.id}': '4', f'fora_{j1.id}': '2', f'primeiro_{j1.id}': 'Arrascaeta',
                f'situacao_{j2.id}': 'fora_prazo'})
    client.post('/interface/api/palpites', json={'participacaoId': bia.id, 'rodadaId': r1.id, 'acao': 'ficar',
                'jogos': {str(j1.id): {'casa': '4', 'fora': '2', 'primeiroGol': 'Arrascaeta'},
                          str(j2.id): {'situacao': 'fora_prazo'}}})
    def resumo(pessoa):
        return sorted((p.jogo_id, p.gols_casa, p.gols_fora, p.primeiro_gol, p.situacao, p.origem)
                      for p in Palpite.query.filter_by(participacao_id=pessoa.id))
    # Ana já tinha 1x0 no jogo 1; Bia não. Ambos acabam com o mesmo conteúdo.
    assert resumo(ana) == resumo(bia)
