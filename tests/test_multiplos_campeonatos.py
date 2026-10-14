"""Vários campeonatos no mesmo bolão e estado automático das rodadas."""
from datetime import datetime, timedelta

from database import db
from models import Bolao, Jogo, Palpite, Participacao, Participante, Resultado, Rodada
from services.estado_rodadas import estados_das_rodadas
from services.ranking import calcular_ranking
from tests.conftest import SENHA_TESTE
from tests.test_interface import entrar, gestao  # noqa: F401


def selecionar(client, bolao_id):
    return client.post('/interface/selecionar', data={'bolao_id': bolao_id})


def test_criar_e_alternar_campeonato_isolado(client, gestao):
    usuario, boloes = gestao
    principal = boloes[0]
    coresp = Participante(nome='Co-responsável', email='co@example.com', senha=SENHA_TESTE)
    ana = Participacao(bolao=principal, nome_exibicao='Ana', email='ana@example.com')
    saiu = Participacao(bolao=principal, nome_exibicao='Saiu', status='removido')
    r1 = Rodada(nome='Rodada 1', campeonato=principal.campeonato)
    jogo = Jogo(time_casa='A', time_fora='B', rodada=r1)
    db.session.add_all([coresp, ana, saiu, jogo,
                        Participacao(bolao=principal, usuario=coresp, nome_exibicao='Co', papel='responsavel')])
    db.session.flush()
    db.session.add_all([Resultado(jogo=jogo, gols_casa_real=1, gols_fora_real=0),
                        Palpite(participacao=ana, jogo=jogo, gols_casa=1, gols_fora=0)])
    db.session.commit()

    entrar(client, usuario)
    selecionar(client, principal.id)
    resposta = client.post('/interface/api/campeonatos', json={'nome': 'Copa do Brasil', 'ano': 2026, 'codigoApi': 'CDB'})
    assert resposta.status_code == 201
    novo = db.session.get(Bolao, resposta.get_json()['bolaoId'])
    assert novo.grupo_id == principal.id and novo.nome == principal.nome
    assert novo.campeonato_id != principal.campeonato_id
    nomes = sorted((p.nome_exibicao, p.papel) for p in novo.participacoes)
    assert nomes == [('Ana', 'participante'), ('Co', 'responsavel'), ('Responsável', 'responsavel')]

    # O novo campeonato já fica selecionado e lista os dois campeonatos do bolão.
    dados = client.get('/interface/api/campeonato').get_json()
    assert dados['campeonato']['nome'] == 'Copa do Brasil' and dados['rodadas'] == []
    assert [c['nome'] for c in dados['campeonatosDoBolao']] == [principal.campeonato.nome, 'Copa do Brasil']

    # Palpites e classificação não se misturam.
    top = client.get('/interface/api/dashboard').get_json()['top5']
    assert all(i['pontos'] == 0 for i in top)
    assert {i['participante'].nome: i['pontos'] for i in calcular_ranking(principal)}['Ana'] == 3

    # O co-responsável também acessa o novo campeonato.
    assert any(p.usuario_id == coresp.id for p in novo.participacoes)
    # Volta ao campeonato original pela seleção normal.
    selecionar(client, principal.id)
    assert client.get('/interface/api/campeonato').get_json()['campeonato']['id'] == principal.campeonato_id


def test_criar_campeonato_valida_dados(client, gestao):
    usuario, boloes = gestao
    entrar(client, usuario)
    selecionar(client, boloes[0].id)
    assert client.post('/interface/api/campeonatos', json={'nome': '', 'ano': 2026}).status_code == 400
    assert client.post('/interface/api/campeonatos', json={'nome': 'X', 'ano': 'abc'}).status_code == 400
    assert Bolao.query.count() == 3


def test_grupo_de_outro_responsavel_nao_aparece(client, gestao):
    usuario, boloes = gestao
    alheio = Bolao(nome='Privado', campeonato=boloes[2].campeonato, criador=boloes[2].criador, grupo_id=boloes[2].id)
    db.session.add(alheio)
    db.session.commit()
    entrar(client, usuario)
    selecionar(client, boloes[0].id)
    lista = client.get('/interface/api/campeonato').get_json()['campeonatosDoBolao']
    assert [c['bolaoId'] for c in lista] == [boloes[0].id]
    assert selecionar(client, alheio.id).status_code == 403


def test_estado_das_rodadas(app, gestao):
    _, boloes = gestao
    bolao = boloes[0]
    ana = Participacao(bolao=bolao, nome_exibicao='Ana')
    passado, futuro = datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=3)
    fechada = Rodada(nome='Rodada 1', campeonato=bolao.campeonato)
    pendente = Rodada(nome='Rodada 2', campeonato=bolao.campeonato)
    aberta = Rodada(nome='Rodada 3', campeonato=bolao.campeonato)
    completa = Rodada(nome='Rodada 4', campeonato=bolao.campeonato)
    vazia = Rodada(nome='Rodada 5', campeonato=bolao.campeonato)
    j1 = Jogo(time_casa='A', time_fora='B', rodada=fechada, data=passado)
    j2 = Jogo(time_casa='C', time_fora='D', rodada=pendente, data=passado)
    j3 = Jogo(time_casa='E', time_fora='F', rodada=aberta, data=futuro)
    j4 = Jogo(time_casa='G', time_fora='H', rodada=completa, data=passado)
    db.session.add_all([ana, j1, j2, j3, j4, vazia])
    db.session.flush()
    db.session.add(Resultado(jogo=j1, gols_casa_real=0, gols_fora_real=0))
    # Rodada 4 já começou, mas todos (responsável e Ana) têm palpite: fica aberta.
    for pessoa in bolao.participacoes:
        db.session.add(Palpite(participacao=pessoa, jogo=j4, gols_casa=1, gols_fora=1))
    db.session.commit()
    rodadas = [fechada, pendente, aberta, completa, vazia]
    estados = {r.nome: e['estado'] for r, e in zip(rodadas, (estados_das_rodadas(bolao, rodadas)[r.id] for r in rodadas))}
    assert estados == {'Rodada 1': 'fechada', 'Rodada 2': 'pendente', 'Rodada 3': 'aberta',
                       'Rodada 4': 'aberta', 'Rodada 5': 'sem_jogos'}


def test_agenda_lista_todas_as_rodadas_para_navegacao(client, gestao):
    usuario, boloes = gestao
    rodadas = [Rodada(nome=f'Rodada {n}', campeonato=boloes[0].campeonato) for n in (2, 1, 3)]
    db.session.add_all([Jogo(time_casa='A', time_fora='B', rodada=r) for r in rodadas])
    db.session.commit()
    entrar(client, usuario)
    selecionar(client, boloes[0].id)
    dados = client.get('/interface/api/jogos').get_json()
    assert [(r['numero'], r['nome']) for r in dados['rodadas']] == [(1, 'Rodada 1'), (2, 'Rodada 2'), (3, 'Rodada 3')]
    assert all(r['estado'] == 'aberta' for r in dados['rodadas'])
    assert dados['rodada']['nome'] == 'Rodada 1'  # primeira com jogo pendente


def test_telas_antigas_nao_mostram_importacao(client, gestao, app):
    usuario, boloes = gestao
    usuario.admin_global = True
    db.session.commit()
    entrar(client, usuario)
    selecionar(client, boloes[0].id)
    for url in (f'/b/{boloes[0].id}/gestao', f'/b/{boloes[0].id}/campeonatos'):
        html = client.get(url).get_data(as_text=True)
        assert 'importar-planilha' not in html and 'importar-jogos' not in html


def test_um_bolao_com_varios_campeonatos_entra_direto(client, app, gestao):
    from tests.test_interface import dados_renderizados
    usuario, boloes = gestao
    for b in boloes[1:2]:
        b.grupo_id = boloes[0].id  # "Amigos B" vira campeonato extra de "Amigos A"
    db.session.commit()
    entrar(client, usuario)
    with dados_renderizados(app) as dados:
        client.get('/interface/')
    assert dados[0]['bolaoAtualId'] == boloes[0].id
    assert {b['grupoId'] for b in dados[0]['boloes']} == {boloes[0].id}
