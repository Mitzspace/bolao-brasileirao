"""Vários campeonatos no mesmo bolão e estado automático das rodadas."""
from datetime import datetime, timedelta

from database import db
from models import Bolao, Jogo, Palpite, Participacao, Resultado, Rodada
from services.estado_rodadas import estados_das_rodadas
from tests.test_interface import entrar, gestao  # noqa: F401


def selecionar(client, bolao_id):
    return client.post('/interface/selecionar', data={'bolao_id': bolao_id})


def test_interface_nao_cria_mais_campeonato_no_mesmo_bolao(client, gestao):
    """Cada campeonato é um bolão separado: novos campeonatos nascem pelo "Novo bolão"."""
    usuario, boloes = gestao
    entrar(client, usuario)
    selecionar(client, boloes[0].id)
    resposta = client.post('/interface/api/campeonatos', json={'nome': 'Copa do Brasil', 'ano': 2026})
    assert resposta.status_code in (404, 405) and 'erro' in resposta.get_json()
    assert Bolao.query.count() == 3
    assert [c['bolaoId'] for c in client.get('/interface/api/campeonato').get_json()['campeonatosDoBolao']] == [boloes[0].id]


def test_migracao_separa_campeonatos_agrupados(app, gestao, tmp_path):
    import sqlite3
    from migrations.separar_campeonatos import migrar
    banco = tmp_path / 'banco.db'
    con = sqlite3.connect(banco)
    con.executescript("""
        CREATE TABLE campeonato (id INTEGER PRIMARY KEY, nome TEXT, ano INTEGER);
        CREATE TABLE bolao (id INTEGER PRIMARY KEY, nome TEXT, campeonato_id INTEGER, grupo_id INTEGER);
        INSERT INTO campeonato VALUES (1, 'Brasileirão', 2026), (2, 'Copa do Brasil', 2026), (3, 'Copa', NULL);
        INSERT INTO bolao VALUES (1, 'Brasileirão 2026', 1, NULL), (2, 'Brasileirão 2026', 2, 1),
                                 (3, 'Outro nome', 3, 1), (4, 'Sozinho', 1, NULL);
    """)
    con.commit()
    con.close()
    backup, renomeados = migrar(banco)
    assert backup.exists() and renomeados == [('Brasileirão 2026', 'Copa do Brasil 2026')]
    con = sqlite3.connect(banco)
    assert con.execute('SELECT id, nome, grupo_id FROM bolao ORDER BY id').fetchall() == [
        (1, 'Brasileirão 2026', None), (2, 'Copa do Brasil 2026', None), (3, 'Outro nome', None), (4, 'Sozinho', None)]
    con.close()
    assert migrar(banco) == (None, [])  # pode rodar de novo sem efeito


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
