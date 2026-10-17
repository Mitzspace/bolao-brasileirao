"""Aba Bolões: lista, classificação completa e criação com as regras da tela atual."""
from database import db
from models import Bolao, Jogo, Palpite, Participacao, Resultado, Rodada
from services.ranking import calcular_ranking
from tests.test_interface import entrar, gestao  # noqa: F401


def preparar(client, gestao):
    usuario, boloes = gestao
    bolao = boloes[0]
    r1 = Rodada(nome='Rodada 1', campeonato=bolao.campeonato)
    r2 = Rodada(nome='Rodada 2', campeonato=bolao.campeonato)
    db.session.add_all([r1, r2])
    db.session.flush()
    j1 = Jogo(time_casa='Flamengo', time_fora='Vasco', rodada=r1)
    j2 = Jogo(time_casa='Santos', time_fora='Bahia', rodada=r2)
    ana = Participacao(bolao=bolao, nome_exibicao='Ana')
    bia = Participacao(bolao=bolao, nome_exibicao='Bia')
    db.session.add_all([j1, j2, ana, bia])
    db.session.flush()
    db.session.add_all([
        Palpite(participacao=ana, jogo=j1, gols_casa=2, gols_fora=1),
        Palpite(participacao=bia, jogo=j1, gols_casa=0, gols_fora=0),
        Palpite(participacao=bia, jogo=j2, gols_casa=1, gols_fora=0),
        Resultado(jogo=j1, gols_casa_real=2, gols_fora_real=1),
        Resultado(jogo=j2, gols_casa_real=1, gols_fora_real=0),
    ])
    db.session.commit()
    entrar(client, usuario)
    return bolao, r1, r2, ana, bia


def test_lista_so_boloes_do_responsavel(client, gestao):
    bolao, *_ = preparar(client, gestao)
    dados = client.get('/interface/api/boloes').get_json()
    assert [b['nome'] for b in dados['boloes']] == ['Amigos A', 'Amigos B']
    a = dados['boloes'][0]
    assert a['participantesAtivos'] == 3 and a['rodada'] == 'Rodada 2'


def test_classificacao_geral_e_por_rodada_igual_ao_ranking(client, gestao):
    bolao, r1, r2, ana, bia = preparar(client, gestao)
    geral = client.get(f'/interface/api/boloes/{bolao.id}/classificacao').get_json()
    esperado = [i['participante'].nome for i in calcular_ranking(bolao)]
    assert [i['nome'] for i in geral['ranking']] == esperado
    assert geral['ranking'][0]['nome'] == 'Ana' and geral['ranking'][0]['pontos'] == 3
    assert geral['variacaoReferencia'] == 'Rodada 2'
    ana_item = next(i for i in geral['ranking'] if i['nome'] == 'Ana')
    assert ana_item['variacao'] == 0  # liderava após a rodada 1 e continua
    assert geral['textoWhatsapp'].splitlines()[:3] == ['*🏆Amigos A*', '', '🟩 1. Ana – 3 pontos']
    assert geral['regras']['classicoExato'] == 5
    rodada = client.get(f'/interface/api/boloes/{bolao.id}/classificacao?rodada_id={r2.id}').get_json()
    assert rodada['ranking'][0]['nome'] == 'Bia' and rodada['ranking'][0]['pontos'] == 3
    assert rodada['textoWhatsapp'].startswith('*🏆Amigos A · Rodada 2*')


def test_classificacao_de_bolao_alheio_e_rodada_alheia(client, gestao):
    bolao, *_ = preparar(client, gestao)
    _, boloes = gestao
    assert client.get(f'/interface/api/boloes/{boloes[2].id}/classificacao').status_code == 404
    alheia = Rodada(nome='Rodada 9', campeonato=boloes[1].campeonato)
    db.session.add(alheia)
    db.session.commit()
    assert client.get(f'/interface/api/boloes/{bolao.id}/classificacao?rodada_id={alheia.id}').status_code == 404


def test_criar_bolao_copiando_nomes(client, gestao):
    bolao, r1, r2, ana, bia = preparar(client, gestao)
    fontes = client.get(f'/interface/api/boloes/fontes?origem_id={bolao.id}').get_json()
    assert {p['nome'] for p in fontes['pessoas']} == {'Ana', 'Bia'}  # o próprio responsável não aparece
    resposta = client.post('/interface/api/boloes', json={
        'nome': 'Novo', 'campeonato': 'Copa', 'ano': '2027', 'codigoApi': 'cl',
        'origemId': bolao.id, 'participacaoIds': [ana.id]})
    assert resposta.status_code == 201
    novo = db.session.get(Bolao, resposta.get_json()['bolaoId'])
    assert novo.campeonato.nome == 'Copa' and novo.campeonato.ano == 2027 and novo.campeonato.codigo_api == 'CL'
    nomes = sorted((p.nome_exibicao, p.papel) for p in novo.participacoes)
    assert nomes == [('Ana', 'participante'), ('Responsável', 'responsavel')]
    assert Palpite.query.join(Participacao).filter(Participacao.bolao_id == novo.id).count() == 0
    with client.session_transaction() as s:
        assert s['bolao_id'] == novo.id


def test_criar_bolao_validacoes(client, gestao):
    bolao, r1, r2, ana, bia = preparar(client, gestao)
    _, boloes = gestao
    base = {'nome': 'Novo', 'campeonato': 'Copa', 'ano': 2027}
    assert client.post('/interface/api/boloes', json={**base, 'nome': 'A'}).status_code == 400
    assert client.post('/interface/api/boloes', json={**base, 'ano': 'x'}).status_code == 400
    assert client.post('/interface/api/boloes', json={**base, 'origemId': boloes[2].id}).status_code == 403
    assert client.post('/interface/api/boloes', json={**base, 'participacaoIds': [ana.id]}).status_code == 403
    assert client.post('/interface/api/boloes', json={**base, 'participacaoIds': ['1']}).status_code == 400
    assert Bolao.query.count() == 3


def test_criar_bolao_exige_csrf(client, gestao, app):
    preparar(client, gestao)
    app.config['WTF_CSRF_ENABLED'] = True
    assert client.post('/interface/api/boloes', json={'nome': 'Novo', 'campeonato': 'Copa', 'ano': 2027}).status_code == 403


def test_faixas_do_texto_compartilhado():
    from services.textos_whatsapp import marcador_posicao
    assert [marcador_posicao(p, 18) for p in (1, 4, 5, 6, 10, 11, 14, 15, 18)] == \
        ['🟩', '🟩', '🟨', '🟦', '🟦', '⬜', '⬜', '🟥', '🟥']
    # Com poucos participantes, as faixas do topo têm prioridade sobre o vermelho.
    assert [marcador_posicao(p, 8) for p in range(1, 9)] == ['🟩'] * 4 + ['🟨'] + ['🟦'] * 3


def test_desempenho_do_participante_pela_classificacao(client, gestao):
    """Classificação do admin: tocar no nome abre o mesmo painel de desempenho do link público."""
    bolao, r1, r2, ana, bia = preparar(client, gestao)
    r = client.get(f'/interface/api/boloes/{bolao.id}/participantes/{bia.id}/desempenho')
    assert r.status_code == 200
    dados = r.get_json()
    assert dados['nome'] == 'Bia' and dados['resumo']['pontos'] == 3 and dados['resumo']['posicao'] == 2
    assert [(e['rodada'], e['pontos']) for e in dados['evolucao']] == [('Rodada 1', 0), ('Rodada 2', 3)]


def test_desempenho_so_de_bolao_gerido_e_participante_do_bolao(client, gestao):
    usuario, boloes = gestao
    bolao, r1, r2, ana, bia = preparar(client, gestao)
    privado = boloes[2]  # de outro responsável
    dono = Participacao.query.filter_by(bolao_id=privado.id).first()
    assert client.get(f'/interface/api/boloes/{privado.id}/participantes/{dono.id}/desempenho').status_code == 404
    # Participante de outro bolão pelo endereço deste bolão: 404.
    assert client.get(f'/interface/api/boloes/{bolao.id}/participantes/{dono.id}/desempenho').status_code == 404
    client.get('/logout')
    assert client.get(f'/interface/api/boloes/{bolao.id}/participantes/{ana.id}/desempenho').status_code == 401
