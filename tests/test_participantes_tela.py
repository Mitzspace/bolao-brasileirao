import json

import pytest
from werkzeug.datastructures import MultiDict

from database import db
from models import Bolao, BonusRodada, Campeonato, Palpite, Participacao, ParticipacaoLog, Resultado, Rodada
from services.gestao_participantes import totais_participantes
from tests.test_acesso_gestao import gestao, sessao


def cliente(gestao):
    client = gestao[0].test_client()
    sessao(client, gestao[1]['responsavel'])
    return client


def test_criar_com_entrada_observacao_sem_login_e_log(gestao):
    client = cliente(gestao)
    response = client.post(f'/b/{gestao[2]}/participacoes/nova', data={
        'nome_exibicao': '  João Novo  ', 'rodada_entrada_id': gestao[4], 'observacao': 'Mensagem recebida'})
    assert response.status_code == 302
    pessoa = Participacao.query.filter_by(nome_exibicao='João Novo').one()
    assert pessoa.usuario_id is None and pessoa.status == 'ativo'
    assert pessoa.rodada_entrada_id == gestao[4] and pessoa.observacao == 'Mensagem recebida'
    log = ParticipacaoLog.query.filter_by(participacao_id=pessoa.id).one()
    assert log.alterado_por == gestao[1]['responsavel']
    assert json.loads(log.valores_novos)['rodada_entrada_id'] == gestao[4]


@pytest.mark.parametrize('rodada', [None, '', 'abc', '999999'])
def test_entrada_obrigatoria_sem_perda_do_formulario(gestao, rodada):
    client = cliente(gestao)
    antes = Participacao.query.count(), ParticipacaoLog.query.count()
    dados = {'nome_exibicao': 'Pessoa nova', 'observacao': 'Não perder observação'}
    if rodada is not None:
        dados['rodada_entrada_id'] = rodada
    response = client.post(f'/b/{gestao[2]}/participacoes/nova', data=dados)
    assert response.status_code == 422
    assert 'Pessoa nova' in response.text and 'Não perder observação' in response.text
    assert 'Selecione uma rodada de entrada deste campeonato.' in response.text
    assert (Participacao.query.count(), ParticipacaoLog.query.count()) == antes


def test_entrada_de_outro_campeonato_e_duplicada_recusadas(gestao):
    client = cliente(gestao)
    outra = Rodada(nome='Rodada 1', campeonato=Campeonato(nome='Outro'))
    db.session.add(outra)
    db.session.commit()
    url = f'/b/{gestao[2]}/participacoes/nova'
    assert client.post(url, data={'nome_exibicao': 'Pessoa nova', 'rodada_entrada_id': outra.id}).status_code == 422
    assert client.post(url, data=MultiDict([
        ('nome_exibicao', 'Pessoa nova'), ('rodada_entrada_id', str(gestao[4])),
        ('rodada_entrada_id', str(outra.id))])).status_code == 422
    assert not Participacao.query.filter_by(nome_exibicao='Pessoa nova').first()


def test_homonimos_aviso_nao_bloqueia_e_nao_confunde_boloes(gestao):
    client = cliente(gestao)
    part = db.session.get(Participacao, gestao[3])
    part.nome_exibicao = 'João Silva'
    db.session.commit()
    response = client.post(f'/b/{gestao[2]}/participacoes/nova', data={
        'nome_exibicao': 'JOAO   SILVA', 'rodada_entrada_id': gestao[4]}, follow_redirects=True)
    assert response.status_code == 200 and 'homônimo real' in response.text
    assert 'Nome repetido neste bolão' in response.text
    assert Participacao.query.filter_by(nome_exibicao='JOAO   SILVA').one().id != part.id
    outro = Bolao(nome='Outro', campeonato_id=part.bolao.campeonato_id, criador_id=gestao[1]['responsavel'])
    db.session.add(Participacao(bolao=outro, nome_exibicao='Nome externo'))
    db.session.commit()
    response = client.post(f'/b/{gestao[2]}/participacoes/nova', data={
        'nome_exibicao': 'Nome externo', 'rodada_entrada_id': gestao[4]}, follow_redirects=True)
    assert 'já existe participante com esse nome' not in response.text


def test_edicao_observacao_limpeza_e_auditoria(gestao):
    client = cliente(gestao)
    url = f'/b/{gestao[2]}/participacoes/{gestao[3]}/editar'
    response = client.post(url, data={'nome_exibicao': 'Nome corrigido', 'observacao': '<script>alert(1)</script>'})
    assert response.status_code == 302
    pessoa = db.session.get(Participacao, gestao[3])
    log = ParticipacaoLog.query.filter_by(participacao_id=pessoa.id).order_by(ParticipacaoLog.id.desc()).first()
    assert json.loads(log.valores_anteriores)['nome_exibicao'] == 'Sem conta'
    assert json.loads(log.valores_novos)['observacao'] == '<script>alert(1)</script>'
    html = client.get(f'/b/{gestao[2]}/participantes').text
    assert '<script>alert(1)</script>' not in html and '&lt;script&gt;' in html
    client.post(url, data={'nome_exibicao': 'Nome corrigido', 'observacao': ''})
    assert pessoa.observacao is None


def test_edicao_invalida_preserva_observacao_e_banco(gestao):
    client = cliente(gestao)
    response = client.post(f'/b/{gestao[2]}/participacoes/{gestao[3]}/editar', data={
        'nome_exibicao': 'X', 'observacao': 'Texto para corrigir'})
    assert response.status_code == 422 and 'Texto para corrigir' in response.text
    assert 'aria-invalid="true"' in response.text
    assert db.session.get(Participacao, gestao[3]).nome_exibicao == 'Sem conta'


def test_filtros_ordem_status_e_sem_exclusao(gestao):
    client = cliente(gestao)
    desistente = Participacao(bolao_id=gestao[2], nome_exibicao='AAA Desistente',
        status='desistente', rodada_desistencia_id=gestao[4])
    removido = Participacao(bolao_id=gestao[2], nome_exibicao='AAA Removido', status='removido')
    db.session.add_all([desistente, removido])
    db.session.commit()
    url = f'/b/{gestao[2]}/participantes'
    html = client.get(url).text
    assert html.index('id="participacao-' + str(gestao[3])) < html.index('id="participacao-' + str(desistente.id))
    assert html.index('id="participacao-' + str(desistente.id)) < html.index('id="participacao-' + str(removido.id))
    assert 'Rodada 1' in html and 'Excluir' not in html and '/excluir' not in html
    ativos = client.get(url + '?filtro=ativos').text
    assert 'AAA Desistente' not in ativos and 'AAA Removido' not in ativos
    desistentes = client.get(url + '?filtro=desistentes').text
    assert 'AAA Desistente' in desistentes and 'Sem conta' not in desistentes
    assert client.get(url + '?filtro=invalido').status_code == 400


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


def test_edicao_e_listagem_recusam_outro_bolao(gestao):
    client = cliente(gestao)
    outro = Bolao(nome='Privado', campeonato_id=db.session.get(Bolao, gestao[2]).campeonato_id,
                  criador_id=gestao[1]['comum'])
    part = Participacao(bolao=outro, nome_exibicao='Segredo')
    db.session.add(part)
    db.session.commit()
    assert client.get(f'/b/{outro.id}/participantes').status_code == 403
    assert client.post(f'/b/{gestao[2]}/participacoes/{part.id}/editar', data={
        'nome_exibicao': 'Invasão', 'observacao': 'Não autorizado'}).status_code == 404
    assert part.nome_exibicao == 'Segredo'


def test_usuario_sem_papel_nao_cria_nem_edita(gestao):
    client = gestao[0].test_client()
    sessao(client, gestao[1]['comum'])
    dados = {'nome_exibicao': 'Teste', 'rodada_entrada_id': gestao[4]}
    assert client.get(f'/b/{gestao[2]}/participantes').status_code == 403
    assert client.post(f'/b/{gestao[2]}/participacoes/nova', data=dados).status_code == 403
    assert client.post(f'/b/{gestao[2]}/participacoes/{gestao[3]}/editar', data=dados).status_code == 403
