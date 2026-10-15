"""Regras de pontuação editáveis por bolão, valendo retroativamente."""
from database import db
from models import Bolao, Jogo, Palpite, Participacao, Resultado, Rodada
from services.grade_palpites import montar_grade
from services.ranking import calcular_ranking
from tests.test_interface import entrar, gestao  # noqa: F401

REGRAS = {'comumExato': 4, 'comumResultado': 2, 'classicoExato': 10, 'classicoResultado': 6, 'primeiroGol': 5}


def preparar(client, gestao):
    usuario, boloes = gestao
    a, b = boloes[0], boloes[1]
    r1 = Rodada(nome='Rodada 1', campeonato=a.campeonato)
    comum = Jogo(time_casa='Santos', time_fora='Bahia', rodada=r1)
    classico = Jogo(time_casa='Grêmio', time_fora='Inter', rodada=r1, classico=True)
    ana = Participacao(bolao=a, nome_exibicao='Ana')
    # Mesmo campeonato em outro bolão, para provar o isolamento das regras.
    b.campeonato = a.campeonato
    bia = Participacao(bolao=b, nome_exibicao='Bia')
    db.session.add_all([comum, classico, ana, bia])
    db.session.flush()
    db.session.add_all([
        Palpite(participacao=ana, jogo=comum, gols_casa=2, gols_fora=0),      # exato comum
        Palpite(participacao=ana, jogo=classico, gols_casa=1, gols_fora=0, primeiro_gol='Braithwaite'),  # resultado + 1º gol
        Palpite(participacao=bia, jogo=comum, gols_casa=2, gols_fora=0),
        Resultado(jogo=comum, gols_casa_real=2, gols_fora_real=0),
        Resultado(jogo=classico, gols_casa_real=2, gols_fora_real=1, primeiro_gol_real='Braithwaite'),
    ])
    classico.primeiro_marcador = 'Braithwaite'
    db.session.commit()
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': a.id})
    return a, b, r1, ana, bia


def pontos(bolao):
    return {i['participante'].nome: i['pontos'] for i in calcular_ranking(bolao)}


def test_padrao_igual_ao_anterior(client, gestao):
    a, b, r1, ana, bia = preparar(client, gestao)
    assert pontos(a)['Ana'] == 3 + 3 + 2
    regras = client.get(f'/interface/api/boloes/{a.id}/classificacao').get_json()['regras']
    assert {k: regras[k] for k in REGRAS} == {'comumExato': 3, 'comumResultado': 1, 'classicoExato': 5,
                                               'classicoResultado': 3, 'primeiroGol': 2}


def test_mudar_regras_recalcula_tudo_e_so_neste_bolao(client, gestao):
    a, b, r1, ana, bia = preparar(client, gestao)
    resposta = client.put(f'/interface/api/boloes/{a.id}/regras', json=REGRAS)
    assert resposta.status_code == 200
    assert pontos(a)['Ana'] == 4 + 6 + 5            # rodada já jogada recalculada
    assert pontos(b)['Bia'] == 3                     # outro bolão continua no padrão
    _, _, _, totais, _ = montar_grade(a, r1)
    assert totais[ana.id]['pontos'] == 15                      # grade usa as mesmas regras
    rodadas = client.get('/interface/api/rodadas').get_json()
    assert rodadas['regras']['classicoExato'] == 10
    # Voltar aos valores antigos devolve a pontuação original.
    client.put(f'/interface/api/boloes/{a.id}/regras', json={'comumExato': 3, 'comumResultado': 1, 'classicoExato': 5,
                                                             'classicoResultado': 3, 'primeiroGol': 2})
    assert pontos(a)['Ana'] == 8


def test_validacao_e_permissao(client, gestao):
    a, b, r1, ana, bia = preparar(client, gestao)
    _, boloes = gestao
    for invalido in ({**REGRAS, 'comumExato': -1}, {**REGRAS, 'primeiroGol': 100}, {**REGRAS, 'comumExato': 'x'},
                     {**REGRAS, 'classicoExato': 2}, {k: v for k, v in REGRAS.items() if k != 'primeiroGol'},
                     {**REGRAS, 'comumResultado': True}):
        assert client.put(f'/interface/api/boloes/{a.id}/regras', json=invalido).status_code == 400
    assert client.put(f'/interface/api/boloes/{boloes[2].id}/regras', json=REGRAS).status_code == 404
    assert db.session.get(Bolao, a.id).pontos_comum_exato == 3


def test_novo_bolao_com_regras(client, gestao):
    preparar(client, gestao)
    r = client.post('/interface/api/boloes', json={'nome': 'Novo', 'campeonato': 'Copa', 'ano': 2027, 'regras': REGRAS})
    novo = db.session.get(Bolao, r.get_json()['bolaoId'])
    assert (novo.pontos_classico_exato, novo.pontos_primeiro_gol) == (10, 5)
    padrao = client.post('/interface/api/boloes', json={'nome': 'Outro', 'campeonato': 'Copa', 'ano': 2027})
    assert db.session.get(Bolao, padrao.get_json()['bolaoId']).pontos_comum_exato == 3
    assert client.post('/interface/api/boloes', json={'nome': 'X1', 'campeonato': 'Copa', 'ano': 2027,
                                                      'regras': {**REGRAS, 'comumExato': 0}}).status_code == 400


def test_migracao_sqlite(tmp_path):
    import sqlite3
    from migrations.regras_bolao import migrar
    banco = tmp_path / 'b.db'
    con = sqlite3.connect(banco)
    con.execute('CREATE TABLE bolao (id INTEGER PRIMARY KEY, nome TEXT)')
    con.execute("INSERT INTO bolao VALUES (1, 'A')")
    con.commit()
    con.close()
    assert migrar(banco).exists()
    con = sqlite3.connect(banco)
    assert con.execute('SELECT pontos_comum_exato, pontos_comum_resultado, pontos_classico_exato, '
                       'pontos_classico_resultado, pontos_primeiro_gol FROM bolao').fetchone() == (3, 1, 5, 3, 2)
    con.close()
    assert migrar(banco) is None
