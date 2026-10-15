"""Cadastro e edição de participantes pela API: mesmas validações, auditoria e isolamento."""
import json

import pytest

from database import db
from models import Bolao, BonusRodada, Campeonato, Palpite, Participacao, ParticipacaoLog, Resultado, Rodada
from services.gestao_participantes import totais_participantes
from tests.test_acesso_gestao import gestao, sessao  # noqa: F401

URL = '/interface/api/participantes'


def cliente(gestao):
    client = gestao[0].test_client()
    sessao(client, gestao[1]['responsavel'])
    return client


def texto(resposta):
    dados = resposta.get_json()
    return json.dumps(dados, ensure_ascii=False)


def test_criar_com_entrada_observacao_sem_login_e_log(gestao):
    client = cliente(gestao)
    response = client.post(URL, json={'nome': '  João Novo  ', 'rodadaEntradaId': gestao[4], 'observacao': 'Mensagem recebida'})
    assert response.status_code == 201
    pessoa = Participacao.query.filter_by(nome_exibicao='João Novo').one()
    assert pessoa.usuario_id is None and pessoa.status == 'ativo'
    assert pessoa.rodada_entrada_id == gestao[4] and pessoa.observacao == 'Mensagem recebida'
    log = ParticipacaoLog.query.filter_by(participacao_id=pessoa.id).one()
    assert log.alterado_por == gestao[1]['responsavel']
    assert json.loads(log.valores_novos)['rodada_entrada_id'] == gestao[4]


@pytest.mark.parametrize('rodada', [None, '', 'abc', 999999])
def test_entrada_obrigatoria(gestao, rodada):
    client = cliente(gestao)
    antes = Participacao.query.count(), ParticipacaoLog.query.count()
    dados = {'nome': 'Pessoa nova', 'observacao': 'Não perder observação'}
    if rodada is not None:
        dados['rodadaEntradaId'] = rodada
    response = client.post(URL, json=dados)
    assert response.status_code == 422
    assert 'Selecione uma rodada de entrada deste campeonato.' in texto(response)
    assert (Participacao.query.count(), ParticipacaoLog.query.count()) == antes


def test_entrada_de_outro_campeonato_recusada(gestao):
    client = cliente(gestao)
    outra = Rodada(nome='Rodada 1', campeonato=Campeonato(nome='Outro'))
    db.session.add(outra)
    db.session.commit()
    assert client.post(URL, json={'nome': 'Pessoa nova', 'rodadaEntradaId': outra.id}).status_code == 422
    assert not Participacao.query.filter_by(nome_exibicao='Pessoa nova').first()


def test_homonimos_bloqueados_sem_confundir_boloes(gestao):
    client = cliente(gestao)
    part = db.session.get(Participacao, gestao[3])
    part.nome_exibicao = 'João Silva'
    db.session.commit()
    response = client.post(URL, json={'nome': 'JOAO   SILVA', 'rodadaEntradaId': gestao[4]})
    assert response.status_code == 422 and 'Já existe participante com esse nome' in texto(response)
    assert Participacao.query.filter_by(nome_exibicao='JOAO   SILVA').first() is None
    outro = Bolao(nome='Outro', campeonato_id=part.bolao.campeonato_id, criador_id=gestao[1]['responsavel'])
    db.session.add(Participacao(bolao=outro, nome_exibicao='Nome externo'))
    db.session.commit()
    assert client.post(URL, json={'nome': 'Nome externo', 'rodadaEntradaId': gestao[4]}).status_code == 201


def test_edicao_observacao_limpeza_e_auditoria(gestao):
    client = cliente(gestao)
    url = f'{URL}/{gestao[3]}'
    assert client.put(url, json={'nome': 'Nome corrigido', 'observacao': '<script>alert(1)</script>'}).status_code == 200
    pessoa = db.session.get(Participacao, gestao[3])
    log = ParticipacaoLog.query.filter_by(participacao_id=pessoa.id).order_by(ParticipacaoLog.id.desc()).first()
    assert json.loads(log.valores_anteriores)['nome_exibicao'] == 'Sem conta'
    assert json.loads(log.valores_novos)['observacao'] == '<script>alert(1)</script>'
    client.put(url, json={'nome': 'Nome corrigido', 'observacao': ''})
    assert pessoa.observacao is None


def test_edicao_invalida_nao_grava(gestao):
    client = cliente(gestao)
    response = client.put(f'{URL}/{gestao[3]}', json={'nome': 'X', 'observacao': 'Texto para corrigir'})
    assert response.status_code == 422
    assert db.session.get(Participacao, gestao[3]).nome_exibicao == 'Sem conta'


def test_ordem_por_status_e_contagens(gestao):
    client = cliente(gestao)
    desistente = Participacao(bolao_id=gestao[2], nome_exibicao='AAA Desistente',
                              status='desistente', rodada_desistencia_id=gestao[4])
    removido = Participacao(bolao_id=gestao[2], nome_exibicao='AAA Removido', status='removido')
    db.session.add_all([desistente, removido])
    db.session.commit()
    dados = client.get(URL).get_json()
    ids = [p['id'] for p in dados['participantes']]
    assert ids.index(gestao[3]) < ids.index(desistente.id) < ids.index(removido.id)
    assert dados['contagens']['desistentes'] == 1


def test_totais_incluem_creditos_e_preservam_removidos(gestao):
    pessoa = db.session.get(Participacao, gestao[3])
    db.session.add_all([
        Palpite(participacao=pessoa, jogo_id=gestao[5], gols_casa=2, gols_fora=1),
        Resultado(jogo_id=gestao[5], gols_casa_real=2, gols_fora_real=1),
        BonusRodada(participacao=pessoa, participante_id=gestao[1]['responsavel'],
                    rodada_id=gestao[4], pontos=2),
    ])
    db.session.commit()
    pessoa.status = 'removido'
    db.session.commit()
    pessoas = Participacao.query.filter_by(bolao_id=gestao[2]).all()
    assert totais_participantes(gestao[2], pessoas)[pessoa.id] == {'pontos': 5, 'palpites': 1}


def test_usuario_sem_papel_nao_cria_nem_edita(gestao):
    client = gestao[0].test_client()
    sessao(client, gestao[1]['comum'])
    dados = {'nome': 'Teste', 'rodadaEntradaId': gestao[4]}
    assert client.get(URL).status_code == 403
    assert client.post(URL, json=dados).status_code == 403
    assert client.put(f'{URL}/{gestao[3]}', json=dados).status_code == 403


def test_email_responsavel_persistem_e_validam(gestao):
    client = cliente(gestao)
    url = f'{URL}/{gestao[3]}'
    dados = {'nome': 'Sem conta', 'email': ' ALBERT@example.com ', 'responsavel': True}
    assert client.put(url, json=dados).status_code == 200
    db.session.expire_all()
    pessoa = db.session.get(Participacao, gestao[3])
    assert pessoa.email == 'albert@example.com' and pessoa.papel == 'responsavel'
    dados.update(email='invalido', responsavel=False)
    assert client.put(url, json=dados).status_code == 422
    db.session.expire_all()
    assert pessoa.email == 'albert@example.com' and pessoa.papel == 'responsavel'
    response = client.post(URL, json={'nome': 'Outro contato', 'email': 'ALBERT@example.com', 'rodadaEntradaId': gestao[4]})
    assert response.status_code == 422
    assert not Participacao.query.filter_by(nome_exibicao='Outro contato').first()


def test_edicao_preserva_ultimo_responsavel(gestao):
    client = cliente(gestao)
    pessoa = Participacao.query.filter_by(bolao_id=gestao[2], usuario_id=gestao[1]['responsavel']).one()
    response = client.put(f'{URL}/{pessoa.id}', json={'nome': pessoa.nome_exibicao, 'responsavel': False})
    assert response.status_code == 409
    db.session.expire_all()
    assert pessoa.papel == 'responsavel'


def test_responsavel_vincula_registro_existente_sem_duplicar(gestao):
    client = cliente(gestao)
    pessoa = db.session.get(Participacao, gestao[3])
    antes = Participacao.query.count()
    dados = {'nome': pessoa.nome_exibicao, 'email': 'novo-responsavel@example.com', 'senha': 'Teste123456!'}
    assert client.post('/interface/api/responsaveis', json=dados).status_code == 409
    assert Participacao.query.count() == antes
    dados['participacaoId'] = pessoa.id
    assert client.post('/interface/api/responsaveis', json=dados).status_code == 201
    db.session.expire_all()
    assert Participacao.query.count() == antes
    assert pessoa.usuario_id is not None and pessoa.papel == 'responsavel'
