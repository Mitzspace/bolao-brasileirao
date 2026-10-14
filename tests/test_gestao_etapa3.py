from urllib.parse import urlsplit, parse_qs
import pytest
from flask import g, url_for
from database import db
from models import Bolao, Campeonato, Jogo, Participacao, Participante, Palpite, PalpiteLog, Resultado, Rodada
from tests.test_acesso_gestao import gestao, sessao


def preparar(gestao):
    app, usuarios, bolao_id, pessoa, rodada, jogo = gestao
    usuario = db.session.get(Participante, usuarios['responsavel'])
    a = db.session.get(Bolao, bolao_id)
    b = Bolao(nome=a.nome, campeonato=a.campeonato, criador=usuario)
    outro = Campeonato(nome='Outro', ano=2027)
    c = Bolao(nome='Outro bolão', campeonato=outro, criador=usuario)
    db.session.add_all([Participacao(bolao=b, usuario=usuario, nome_exibicao='Gestor B', papel='responsavel'),
        Participacao(bolao=c, usuario=usuario, nome_exibicao='Gestor C', papel='responsavel')])
    j = Jogo(time_casa='X', time_fora='Y', rodada=Rodada(nome='Rodada 1', campeonato=outro))
    db.session.add(j)
    db.session.commit()
    client = app.test_client()
    sessao(client, usuario.id)
    return client, a, b, c, j


def test_urls_canonicas_abas_e_compatibilidade_post(gestao):
    client, a, b, c, j = preparar(gestao)
    for bolao in [a, b, a]:
        html = client.get(f'/b/{bolao.id}/ranking').text
        assert f'/b/{bolao.id}/palpites' in html
    resposta = client.get(f'/ranking?bolao_id={a.id}')
    assert resposta.status_code == 302 and resposta.location == f'/b/{a.id}/ranking'
    _, _, _, pessoa, rodada, jogo = gestao
    form = {'participante_id': pessoa, 'rodada_id': rodada, f'casa_{jogo}': '2', f'fora_{jogo}': '1'}
    resposta = client.post(f'/admin/palpites?bolao_id={a.id}', data=form)
    assert resposta.status_code == 307 and Palpite.query.count() == 0
    client.post(resposta.location, data=form)
    assert Palpite.query.one().participacao_id == pessoa
    assert PalpiteLog.query.count() == 1
    assert client.get(f'/b/{a.id}/ranking?bolao_id={b.id}').status_code == 403
    assert client.post(f'/b/{a.id}/palpites', data={**form, 'bolao_id': b.id}).status_code == 403


@pytest.mark.parametrize('aba,sufixo', [('admin.gerenciar_palpites', 'palpites'),
    ('admin.cadastrar_resultados', 'resultados'), ('admin.listar_participantes', 'participantes'),
    ('admin.responsaveis', 'configuracoes')])
def test_troca_aba_e_rodada_administrativa(gestao, aba, sufixo):
    client, a, b, c, j = preparar(gestao)
    for destino in [b, c]:
        r = client.post('/boloes/selecionar', data={'bolao_id': destino.id,
            'bolao_origem_id': a.id, 'aba_origem': aba, 'rodada_origem_id': gestao[4]})
        assert urlsplit(r.location).path == f'/b/{destino.id}/{sufixo}'
        parametros = parse_qs(urlsplit(r.location).query)
        assert ('rodada_id' in parametros) == (destino == b and sufixo in {'palpites', 'resultados'})
        assert client.get(r.location).status_code == 200


@pytest.mark.parametrize('sufixo', ['jogo/{j}/editar', 'jogo/{j}/encerrar', 'jogo/{j}/reabrir',
    'jogo/{j}/excluir', 'rodada/{r}/toggle-aberta', 'rodada/{r}/excluir',
    'campeonato/{c}/editar', 'campeonato/{c}/excluir'])
def test_ids_de_outro_campeonato_bloqueados(gestao, sufixo):
    client, a, b, c, j = preparar(gestao)
    url = sufixo.format(j=j.id, r=j.rodada_id, c=c.campeonato_id)
    assert client.post(f'/b/{a.id}/{url}').status_code == 404
    assert not j.encerrado


@pytest.mark.parametrize('sufixo,form', [('resultados', 'jogo_id'), ('jogo', 'rodada_id'),
                                      ('rodada', 'campeonato_id')])
def test_formularios_nao_gravam_fora_do_escopo(gestao, sufixo, form):
    client, a, b, c, j = preparar(gestao)
    valor = {'jogo_id': j.id, 'rodada_id': j.rodada_id, 'campeonato_id': c.campeonato_id}[form]
    assert client.post(f'/b/{a.id}/{sufixo}', data={form: valor}).status_code == 404
    assert Resultado.query.count() == 0


def test_responsaveis_adicionar_remover_preservar_e_ultimo(gestao):
    client, a, b, c, j = preparar(gestao)
    proprio = Participacao.query.filter_by(bolao_id=a.id, usuario_id=gestao[1]['responsavel']).one()
    url = f'/b/{a.id}/configuracoes'
    assert client.post(url, data={'acao': 'remover', 'participacao_id': proprio.id}).status_code == 409
    assert proprio.papel == 'responsavel'
    original = Participacao.query.filter_by(bolao_id=a.id, usuario_id=gestao[1]['comum']).one()
    db.session.add(Palpite(participacao=original, jogo_id=gestao[5], gols_casa=1, gols_fora=0))
    db.session.commit()
    assert client.post(url, data={'acao': 'adicionar', 'email': 'comum@teste.com', 'senha': 'ignorada'}).status_code == 302
    assert original.papel == 'responsavel'
    assert Participacao.query.filter_by(bolao_id=b.id, usuario_id=gestao[1]['comum']).count() == 0
    assert client.post(url, data={'acao': 'remover', 'participacao_id': original.id}).status_code == 302
    assert original.papel == 'participante' and original.status == 'ativo'
    assert Palpite.query.count() == PalpiteLog.query.count() == 1
    assert client.post(url, data={'acao': 'adicionar', 'email': 'novo@teste.com', 'nome': 'Novo Gestor', 'senha': 'senha123'}).status_code == 302
    novo = Participante.query.filter_by(email='novo@teste.com').one()
    assert not novo.admin_global and not novo.admin
    assert Participacao.query.filter_by(bolao_id=a.id, usuario_id=novo.id).one().papel == 'responsavel'


def test_acesso_removido_e_responsavel_sem_conta_nao_conta_como_substituto(gestao):
    client, a, b, c, j = preparar(gestao)
    sem_conta = db.session.get(Participacao, gestao[3])
    sem_conta.papel = 'responsavel'
    db.session.commit()
    proprio = Participacao.query.filter_by(bolao_id=a.id, usuario_id=gestao[1]['responsavel']).one()
    assert client.post(f'/b/{a.id}/configuracoes', data={'acao': 'remover', 'participacao_id': proprio.id}).status_code == 409
    proprio.papel = 'participante'
    db.session.commit()
    assert client.get(f'/b/{a.id}/ranking').status_code == 403
    assert client.get(f'/b/{b.id}/ranking').status_code == 200


@pytest.mark.parametrize('sufixo', ['sync', 'importar-planilha', 'importar-resultados', 'importar-jogos'])
def test_ferramentas_globais_exigem_admin_global(gestao, sufixo):
    client, a, b, c, j = preparar(gestao)
    assert client.get(f'/b/{a.id}/{sufixo}').status_code == 403


def test_csrf_e_troca_sem_hover(gestao):
    client, a, b, c, j = preparar(gestao)
    app = gestao[0]
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post(f'/b/{a.id}/configuracoes', data={'acao': 'adicionar', 'email': 'comum@teste.com'}).status_code == 403
    html = client.get(f'/b/{a.id}/palpites?rodada_id={gestao[4]}').text
    assert '<details' in html and '<summary' in html
    assert f'name="rodada_origem_id" value="{gestao[4]}"' in html
    assert 'name="csrf_token"' in html
