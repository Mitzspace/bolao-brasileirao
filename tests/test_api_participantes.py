"""Aba Participantes pela API: mesmas regras da tela atual, com evolução por rodada."""
from database import db
from models import Jogo, Palpite, ParticipacaoLog, Participacao, Resultado, Rodada
from services.ranking import calcular_ranking
from tests.test_interface import entrar, gestao  # noqa: F401


def preparar(client, gestao):
    usuario, boloes = gestao
    bolao = boloes[0]
    rodadas = [Rodada(nome=f'Rodada {i}', campeonato=bolao.campeonato) for i in (1, 2, 3)]
    db.session.add_all(rodadas)
    db.session.flush()
    jogos = [Jogo(time_casa='Santos', time_fora='Bahia', rodada=r) for r in rodadas]
    ana = Participacao(bolao=bolao, nome_exibicao='Ana', rodada_entrada=rodadas[0])
    bia = Participacao(bolao=bolao, nome_exibicao='Bia', rodada_entrada=rodadas[0])
    db.session.add_all(jogos + [ana, bia])
    db.session.flush()
    # Rodada 1: Ana crava (3), Bia erra. Rodada 2: Bia crava, Ana acerta resultado (1).
    db.session.add_all([
        Palpite(participacao=ana, jogo=jogos[0], gols_casa=2, gols_fora=1),
        Palpite(participacao=bia, jogo=jogos[0], gols_casa=0, gols_fora=1),
        Palpite(participacao=ana, jogo=jogos[1], gols_casa=1, gols_fora=0),
        Palpite(participacao=bia, jogo=jogos[1], gols_casa=3, gols_fora=0),
        Palpite(participacao=ana, jogo=jogos[2], gols_casa=1, gols_fora=1),
        Resultado(jogo=jogos[0], gols_casa_real=2, gols_fora_real=1),
        Resultado(jogo=jogos[1], gols_casa_real=3, gols_fora_real=0),
    ])
    db.session.commit()
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': bolao.id})
    return bolao, rodadas, jogos, ana, bia


def test_lista_com_pontos_posicao_e_variacao(client, gestao):
    bolao, rodadas, jogos, ana, bia = preparar(client, gestao)
    dados = client.get('/interface/api/participantes').get_json()
    pessoas = {p['nome']: p for p in dados['participantes']}
    assert pessoas['Ana']['pontos'] == 4 and pessoas['Bia']['pontos'] == 3
    assert pessoas['Ana']['posicao'] == 1 and pessoas['Ana']['variacao'] == 0
    assert pessoas['Ana']['palpites'] == 3 and pessoas['Ana']['cravadas'] == 1
    assert pessoas['Responsável']['responsavel'] and pessoas['Responsável']['souEu']
    assert dados['contagens'] == {'todos': 3, 'ativos': 3, 'desistentes': 0}
    assert 'pagamento' not in pessoas['Ana'] and 'telefone' not in pessoas['Ana']


def test_evolucao_igual_ao_ranking_acumulado(client, gestao):
    bolao, rodadas, jogos, ana, bia = preparar(client, gestao)
    dados = client.get(f'/interface/api/participantes/{bia.id}').get_json()
    assert [e['curto'] for e in dados['evolucao']] == ['R1', 'R2']  # até a última rodada com resultado
    assert [e['pontos'] for e in dados['evolucao']] == [0, 3]
    for e, rodada in zip(dados['evolucao'], rodadas):
        ref = calcular_ranking(bolao, ate_rodada=rodada)
        posicao = next(i for i, item in enumerate(ref, 1) if item['participante'].id == bia.id)
        assert e['posicao'] == posicao and e['acumulado'] == ref[posicao - 1]['pontos']


def test_criar_editar_e_validar(client, gestao):
    bolao, rodadas, jogos, ana, bia = preparar(client, gestao)
    ruim = client.post('/interface/api/participantes', json={'nome': 'ana', 'rodadaEntradaId': None})
    assert ruim.status_code == 422
    assert set(ruim.get_json()['erros']) == {'nome_exibicao', 'rodada_entrada_id'}
    novo = client.post('/interface/api/participantes', json={'nome': 'Caio', 'email': 'CAIO@x.com',
                       'rodadaEntradaId': rodadas[1].id, 'observacao': ' paga em dia '})
    assert novo.status_code == 201
    caio = db.session.get(Participacao, novo.get_json()['id'])
    assert (caio.email, caio.rodada_entrada_id, caio.papel, caio.usuario_id) == ('caio@x.com', rodadas[1].id, 'participante', None)
    assert client.put(f'/interface/api/participantes/{caio.id}', json={'nome': 'Caio S.', 'email': '',
                      'responsavel': False, 'observacao': ''}).status_code == 200
    db.session.refresh(caio)
    assert (caio.nome_exibicao, caio.email, caio.observacao) == ('Caio S.', None, None)
    assert client.put(f'/interface/api/participantes/{caio.id}', json={'nome': 'Bia'}).status_code == 422
    assert ParticipacaoLog.query.filter_by(participacao_id=caio.id).count() >= 2  # auditoria continua


def test_mesmo_resultado_da_tela_antiga(client, gestao):
    bolao, rodadas, jogos, ana, bia = preparar(client, gestao)
    client.post('/b/%d/participacoes/nova' % bolao.id, data={'nome_exibicao': 'Velho', 'email': 'v@x.com',
                'rodada_entrada_id': rodadas[1].id, 'observacao': 'obs'})
    client.post('/interface/api/participantes', json={'nome': 'Novo', 'email': 'n@x.com',
                'rodadaEntradaId': rodadas[1].id, 'observacao': 'obs'})
    velho = Participacao.query.filter_by(nome_exibicao='Velho').one()
    novo = Participacao.query.filter_by(nome_exibicao='Novo').one()
    campos = lambda p: (p.papel, p.status, p.rodada_entrada_id, p.observacao, p.usuario_id)
    assert campos(velho) == campos(novo)


def test_remover_e_reativar(client, gestao):
    bolao, rodadas, jogos, ana, bia = preparar(client, gestao)
    r = client.post(f'/interface/api/participantes/{ana.id}/status', json={'acao': 'remover'})
    assert r.status_code == 200 and r.get_json()['logout'] is False
    db.session.refresh(ana)
    assert ana.status == 'removido' and Palpite.query.filter_by(participacao_id=ana.id).count() == 3
    client.post(f'/interface/api/participantes/{ana.id}/status', json={'acao': 'reativar'})
    db.session.refresh(ana)
    assert ana.status == 'ativo'
    assert client.post(f'/interface/api/participantes/{ana.id}/status', json={'acao': 'x'}).status_code == 400
    # Último responsável não pode sair.
    eu = Participacao.query.filter_by(bolao_id=bolao.id, papel='responsavel').one()
    resposta = client.post(f'/interface/api/participantes/{eu.id}/status', json={'acao': 'remover'})
    assert resposta.status_code == 409 and 'responsável' in resposta.get_json()['erro']


def test_desistencia_previa_e_confirmacao(client, gestao):
    bolao, rodadas, jogos, ana, bia = preparar(client, gestao)
    url = f'/interface/api/participantes/{ana.id}/desistencia'
    previa = client.post(url, json={'acao': 'registrar', 'rodadaId': rodadas[1].id, 'motivo': 'viajou'})
    assert previa.status_code == 200
    dados = previa.get_json()
    assert len(dados['previa']['posteriores']) == 2  # rodadas 2 e 3
    db.session.refresh(ana)
    assert ana.status == 'ativo'  # prévia não grava
    falso = client.post(url, json={'acao': 'registrar', 'rodadaId': rodadas[1].id, 'motivo': 'outro',
                                   'confirmar': True, 'token': dados['token']})
    assert falso.status_code == 409  # dados mudaram desde a prévia
    ok = client.post(url, json={'acao': 'registrar', 'rodadaId': rodadas[1].id, 'motivo': 'viajou',
                                'confirmar': True, 'token': dados['token']})
    assert ok.status_code == 200
    db.session.refresh(ana)
    assert (ana.status, ana.rodada_desistencia_id, ana.motivo_desistencia) == ('desistente', rodadas[1].id, 'viajou')
    pontos = {i['participante'].nome: i['pontos'] for i in calcular_ranking(bolao)}
    assert pontos['Ana'] == 3  # só a rodada 1 continua valendo
    detalhe = client.get(f'/interface/api/participantes/{ana.id}').get_json()
    assert len(detalhe['guardados']) == 2 and detalhe['historico'][0]['acao'] == 'Desistência'
    # Reativar exige decidir sobre os palpites guardados.
    previa = client.post(url, json={'acao': 'reativar'}).get_json()
    assert len(previa['previa']['restauraveis']) == 2
    sem_decisao = client.post(url, json={'acao': 'reativar', 'confirmar': True, 'token': previa['token']})
    assert sem_decisao.status_code == 422
    client.post(url, json={'acao': 'reativar', 'confirmar': True, 'token': previa['token'], 'restaurar': 'sim'})
    db.session.refresh(ana)
    assert ana.status == 'ativo' and {i['participante'].nome: i['pontos'] for i in calcular_ranking(bolao)}['Ana'] == 4


def test_desistencia_valida_rodada(client, gestao):
    bolao, rodadas, jogos, ana, bia = preparar(client, gestao)
    caio = Participacao(bolao=bolao, nome_exibicao='Caio', rodada_entrada=rodadas[2])
    db.session.add(caio)
    db.session.commit()
    url = f'/interface/api/participantes/{caio.id}/desistencia'
    assert client.post(url, json={'acao': 'registrar'}).status_code == 422
    r = client.post(url, json={'acao': 'registrar', 'rodadaId': rodadas[0].id})
    assert r.status_code == 422 and 'entrada' in r.get_json()['erro']


def test_isolamento_entre_boloes(client, gestao):
    preparar(client, gestao)
    _, boloes = gestao
    alheia = Participacao(bolao=boloes[2], nome_exibicao='Alheia')
    db.session.add(alheia)
    db.session.commit()
    assert client.get(f'/interface/api/participantes/{alheia.id}').status_code == 404
    assert client.put(f'/interface/api/participantes/{alheia.id}', json={'nome': 'X'}).status_code == 404
    assert client.post(f'/interface/api/participantes/{alheia.id}/status', json={'acao': 'remover'}).status_code == 404
