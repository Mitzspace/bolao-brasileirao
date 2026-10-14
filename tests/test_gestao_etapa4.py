import pytest
from database import db
from models import Bolao, BonusRodada, Campeonato, Participacao, Participante, Palpite, PalpiteLog
from tests.test_acesso_gestao import gestao, sessao


def cliente(gestao):
    client = gestao[0].test_client()
    sessao(client, gestao[1]['responsavel'])
    return client


def test_criacao_copia_nomes_sem_contas_palpites_ou_creditos(gestao):
    client = cliente(gestao)
    origem = db.session.get(Bolao, gestao[2])
    sem_conta = db.session.get(Participacao, gestao[3])
    com_conta = Participacao.query.filter_by(bolao_id=origem.id, usuario_id=gestao[1]['comum']).one()
    com_conta.status = 'removido'
    com_conta.papel = 'responsavel'
    db.session.add(Palpite(participacao=sem_conta, jogo_id=gestao[5], gols_casa=2, gols_fora=0))
    outro = Campeonato(nome='Outra competição', ano=2027)
    db.session.add(outro)
    db.session.commit()
    usuarios_antes = Participante.query.count()
    resposta = client.post('/boloes/novo', data={'nome': origem.nome, 'campeonato_nome': outro.nome, 'campeonato_ano': outro.ano,
        'origem_id': origem.id, 'participacao_ids': [sem_conta.id, com_conta.id, sem_conta.id]})
    assert resposta.status_code == 302
    novo = Bolao.query.order_by(Bolao.id.desc()).first()
    assert resposta.location == f'/b/{novo.id}/participantes'
    assert novo.id != origem.id and novo.campeonato_id != outro.id and novo.campeonato.nome == outro.nome
    assert not novo.permite_palpite_proprio and novo.permite_lancamento_por_responsavel
    copias = Participacao.query.filter_by(bolao_id=novo.id, papel='participante').all()
    assert {p.nome_exibicao for p in copias} == {sem_conta.nome_exibicao, com_conta.nome_exibicao}
    assert len(copias) == 2
    for p in copias:
        assert p.usuario_id is None and p.participante_legado_id is None
        assert p.status == 'ativo' and not p.palpites and not p.creditos_historicos
    assert Participacao.query.filter_by(bolao_id=novo.id, papel='responsavel').one().usuario_id == gestao[1]['responsavel']
    assert Participante.query.count() == usuarios_antes
    assert Palpite.query.count() == PalpiteLog.query.count() == 1
    assert com_conta.status == 'removido' and com_conta.papel == 'responsavel'
    with client.session_transaction() as s:
        assert s['bolao_id'] == novo.id
    assert client.get(resposta.location).status_code == 200


def test_primeiro_bolao_admin_global_sem_bolao_ativo(gestao):
    client = gestao[0].test_client()
    sessao(client, gestao[1]['global'])
    assert client.get('/boloes/novo').status_code == 200
    origem = db.session.get(Bolao, gestao[2])
    response = client.post('/boloes/novo', data={'nome': 'Primeiro', 'campeonato_nome': 'Brasileirão', 'campeonato_ano': 2026})
    assert response.status_code == 302
    novo = Bolao.query.order_by(Bolao.id.desc()).first()
    assert len(novo.participacoes) == 1 and novo.participacoes[0].usuario_id == gestao[1]['global']


@pytest.mark.parametrize('campo,valor,status', [('nome', '', 400), ('nome', 'A' * 101, 400),
    ('campeonato_id', '99999', 400), ('origem_id', '99999', 403),
    ('participacao_ids', '99999', 403), ('participacao_ids', 'texto', 400)])
def test_criacao_invalida_nao_grava_parcialmente(gestao, campo, valor, status):
    client = cliente(gestao)
    origem = db.session.get(Bolao, gestao[2])
    antes = (Bolao.query.count(), Participacao.query.count(), Campeonato.query.count())
    dados = {'nome': 'Novo', 'campeonato_nome': 'Brasileirão', 'campeonato_ano': 2026, 'origem_id': origem.id}
    dados[campo] = valor
    assert client.post('/boloes/novo', data=dados).status_code == status
    assert (Bolao.query.count(), Participacao.query.count(), Campeonato.query.count()) == antes


def test_fonte_sem_permissao_e_participacao_de_outra_fonte(gestao):
    client = cliente(gestao)
    a = db.session.get(Bolao, gestao[2])
    outro = Bolao(nome='Privado', campeonato=a.campeonato, criador_id=gestao[1]['comum'])
    part = Participacao(bolao=outro, nome_exibicao='Não autorizado')
    db.session.add(part)
    db.session.commit()
    assert client.get(f'/boloes/novo?origem_id={outro.id}').status_code == 403
    assert client.post('/boloes/novo', data={'nome':'Teste', 'campeonato_nome':'Brasileirão', 'campeonato_ano':2026,
        'origem_id':a.id,'participacao_ids':part.id}).status_code == 403
    assert 'Não autorizado' not in client.get(f'/boloes/novo?origem_id={a.id}').text


def test_cadastro_edicao_remocao_reativacao_preservam_historico(gestao):
    client = cliente(gestao)
    bolao = gestao[2]
    usuarios = Participante.query.count()
    assert client.post(f'/b/{bolao}/participacoes/nova', data={'nome_exibicao':'Nome sem conta', 'rodada_entrada_id': gestao[4]}).status_code == 302
    pessoa = Participacao.query.order_by(Participacao.id.desc()).first()
    assert pessoa.usuario_id is None and pessoa.participante_legado_id is None
    assert Participante.query.count() == usuarios
    db.session.add(Palpite(participacao=pessoa, jogo_id=gestao[5], gols_casa=1, gols_fora=1))
    db.session.commit()
    datas = pessoa.entrou_em, pessoa.pontua_desde
    assert client.post(f'/b/{bolao}/participacoes/{pessoa.id}/editar', data={'nome_exibicao':'Novo nome'}).status_code == 302
    assert pessoa.nome_exibicao == 'Novo nome'
    url = f'/b/{bolao}/participacoes/{pessoa.id}/status'
    assert client.post(url, data={'acao':'remover'}).status_code == 302
    assert pessoa.status == 'removido' and pessoa.saiu_em is not None
    assert client.post(f'/b/{bolao}/palpites', data={'participante_id':pessoa.id,'rodada_id':gestao[4]}).status_code == 404
    assert client.post(url, data={'acao':'reativar'}).status_code == 302
    assert pessoa.status == 'ativo' and pessoa.saiu_em is None
    assert (pessoa.entrou_em, pessoa.pontua_desde) == datas
    assert Palpite.query.count() == PalpiteLog.query.count() == 1


def test_ultimo_responsavel_nao_pode_ser_removido_pelo_crud(gestao):
    client = cliente(gestao)
    proprio = Participacao.query.filter_by(usuario_id=gestao[1]['responsavel'],bolao_id=gestao[2]).one()
    assert client.post(f'/b/{gestao[2]}/participacoes/{proprio.id}/status', data={'acao':'remover'}).status_code == 409
    assert proprio.status == 'ativo'


def test_editar_nome_local_nao_altera_conta_e_reativar_nao_restaura_acesso(gestao):
    client = cliente(gestao)
    part = Participacao.query.filter_by(usuario_id=gestao[1]['comum'],bolao_id=gestao[2]).one()
    nome_conta = part.usuario.nome
    client.post(f'/b/{gestao[2]}/participacoes/{part.id}/editar', data={'nome_exibicao':'Nome local'})
    assert part.usuario.nome == nome_conta
    part.papel = 'responsavel'
    part.status = 'saiu'
    db.session.commit()
    client.post(f'/b/{gestao[2]}/participacoes/{part.id}/status', data={'acao':'reativar'})
    assert part.status == 'ativo' and part.papel == 'participante'


@pytest.mark.parametrize('sufixo,dados', [('editar', {'nome_exibicao':'Alterado'}), ('status', {'acao':'remover'})])
def test_crud_recusa_id_de_outro_bolao(gestao,sufixo,dados):
    client=cliente(gestao)
    b=db.session.get(Bolao,gestao[2])
    outro=Bolao(nome='Outro',campeonato=b.campeonato,criador_id=gestao[1]['comum'])
    p=Participacao(bolao=outro,nome_exibicao='Privado')
    db.session.add(p); db.session.commit()
    assert client.post(f'/b/{b.id}/participacoes/{p.id}/{sufixo}',data=dados).status_code==404
    assert p.nome_exibicao=='Privado' and p.status=='ativo'


def test_csrf_e_permissoes_criacao(gestao):
    client=cliente(gestao)
    gestao[0].config['WTF_CSRF_ENABLED']=True
    assert client.post('/boloes/novo',data={'nome':'Teste'}).status_code==403
    assert client.post(f'/b/{gestao[2]}/participacoes/nova',data={'nome_exibicao':'Teste'}).status_code==403
    sessao(client,gestao[1]['comum'])
    assert client.get('/boloes/novo').status_code==403


@pytest.mark.parametrize('campo,valor', [('campeonato_nome', ''), ('campeonato_ano', 'abc'), ('campeonato_ano', '0')])
def test_campeonato_proprio_invalido_nao_cria_bolao(gestao, campo, valor):
    client = cliente(gestao)
    antes = (Bolao.query.count(), Campeonato.query.count())
    dados = {'nome': 'Novo', 'campeonato_nome': 'Brasileirão', 'campeonato_ano': 2026}
    dados[campo] = valor
    assert client.post('/boloes/novo', data=dados).status_code == 400
    assert (Bolao.query.count(), Campeonato.query.count()) == antes


def test_boloes_mesma_temporada_tem_campeonatos_independentes(gestao):
    client = cliente(gestao)
    ids = []
    for nome in ['Bolão A', 'Bolão B']:
        assert client.post('/boloes/novo', data={'nome': nome, 'campeonato_nome': 'Brasileirão',
            'campeonato_ano': 2026}).status_code == 302
        ids.append(Bolao.query.order_by(Bolao.id.desc()).first().campeonato_id)
    assert ids[0] != ids[1]
