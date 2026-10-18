"""Área pública (link sem login): regras de visibilidade e segurança com casos concretos."""
import json
import re
from datetime import datetime, timedelta

import pytest

from database import db
from models import Jogo, Palpite, Participacao, Participante, Resultado, Rodada
from services import cache_publico
from tests.test_interface import entrar, gestao  # noqa: F401


@pytest.fixture
def cenario(client, gestao):
    """Bolão com 2 rodadas:
    - Rodada 1: Flamengo x Vasco COM resultado (2x1) e Santos x Bahia SEM resultado, mas já iniciado
      e marcado 'encerrado' (botão Encerrar para palpites).
    - Rodada 2: Grêmio x Inter no futuro, com palpites lançados.
    Ana (ativa, com e-mail) e Bia (desistente a partir da rodada 2).
    """
    usuario, boloes = gestao
    bolao = boloes[0]
    r1 = Rodada(nome='1ª Rodada', campeonato=bolao.campeonato)
    r2 = Rodada(nome='2ª Rodada', campeonato=bolao.campeonato)
    db.session.add_all([r1, r2])
    db.session.flush()
    passado = datetime.now() - timedelta(days=1)
    j1 = Jogo(time_casa='Flamengo', time_fora='Vasco', rodada=r1, data=passado, ordem=1, classico=True)
    j2 = Jogo(time_casa='Santos', time_fora='Bahia', rodada=r1, data=passado, ordem=2, encerrado=True)
    j3 = Jogo(time_casa='Grêmio', time_fora='Internacional', rodada=r2, data=datetime.now() + timedelta(days=3))
    ana = Participacao(bolao=bolao, nome_exibicao='Ana Souza', email='ana@segredo.com', observacao='paga em dia')
    bia = Participacao(bolao=bolao, nome_exibicao='Bia', status='desistente', rodada_desistencia=r2,
                       motivo_desistencia='mudou de cidade')
    db.session.add_all([j1, j2, j3, ana, bia])
    db.session.flush()
    db.session.add(Resultado(jogo=j1, gols_casa_real=2, gols_fora_real=1))
    db.session.add_all([
        Palpite(participacao=ana, jogo=j1, gols_casa=2, gols_fora=1, primeiro_gol='Pedro'),  # cravada clássico
        Palpite(participacao=bia, jogo=j1, gols_casa=0, gols_fora=0),
        Palpite(participacao=ana, jogo=j2, gols_casa=7, gols_fora=7),  # jogo sem resultado
        Palpite(participacao=ana, jogo=j3, gols_casa=9, gols_fora=8),  # jogo futuro
    ])
    db.session.commit()
    cache_publico.invalidar()
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': bolao.id})
    link = client.post(f'/interface/api/boloes/{bolao.id}/publico/link', json={'acao': 'gerar'}).get_json()['link']
    codigo = link.rsplit('/', 1)[1]
    client.get('/logout')
    return {'bolao': bolao, 'usuario': usuario, 'codigo': codigo, 'r1': r1, 'r2': r2,
            'base': f'/publico/{codigo}', 'ana': ana, 'bia': bia}


def liberar(client, c, rodada):
    entrar(client, c['usuario'])
    r = client.put(f"/interface/api/boloes/{c['bolao'].id}/publico/tabela",
                   json={'rodadaId': rodada.id if rodada else None})
    assert r.status_code == 200, r.get_json()
    client.get('/logout')
    return r.get_json()


def todo_json(client, c):
    rotas = ['/api/inicio', '/api/classificacao', '/api/classificacao?desistentes=mostrar', '/api/jogos',
             '/api/jogos?rodada=1', '/api/jogos?rodada=2', '/api/palpites', '/api/palpites?rodada=1',
             '/api/palpites?rodada=2', '/api/participantes']
    respostas = {rota: client.get(c['base'] + rota) for rota in rotas}
    for p in respostas['/api/participantes'].get_json()['participantes']:
        rota = f"/api/participantes/{p['ref']}"
        respostas[rota] = client.get(c['base'] + rota)
    return respostas


# ---------- Palpites: só jogos com resultado ----------

def test_jogo_futuro_com_palpite_nao_aparece(client, cenario):
    r2 = client.get(cenario['base'] + '/api/palpites?rodada=2')
    assert r2.status_code == 200
    jogo = r2.get_json()['jogos'][0]
    assert jogo['casa'] == 'Grêmio' and jogo['revelado'] is False and 'palpites' not in jogo
    assert '"casa":9' not in r2.get_data(as_text=True).replace(' ', '')


def test_jogo_encerrado_para_palpites_sem_resultado_nao_revela(client, cenario):
    """'Encerrar para palpites' não é jogo acontecido: sem placar, nada aparece."""
    jogos = client.get(cenario['base'] + '/api/palpites?rodada=1').get_json()['jogos']
    santos = next(j for j in jogos if j['casa'] == 'Santos')
    assert santos['revelado'] is False and 'palpites' not in santos


def test_jogo_com_resultado_mostra_palpites(client, cenario):
    liberar(client, cenario, cenario['r1'])
    jogos = client.get(cenario['base'] + '/api/palpites?rodada=1').get_json()['jogos']
    fla = next(j for j in jogos if j['casa'] == 'Flamengo')
    assert fla['revelado'] is True and (fla['golsCasa'], fla['golsFora']) == (2, 1)
    por_nome = {p['nome']: p for p in fla['palpites']}
    ana = dict(por_nome['Ana Souza'])
    assert re.fullmatch(r'[0-9a-f]{16}', ana.pop('ref'))
    assert ana == {'nome': 'Ana Souza', 'status': 'ativo', 'situacao': 'valido',
                   'casa': 2, 'fora': 1, 'primeiroGol': 'Pedro', 'pontos': 5}
    assert por_nome['Bia']['casa'] == 0


def test_nenhuma_resposta_publica_contem_palpite_de_jogo_sem_resultado(client, cenario):
    for rota, r in todo_json(client, cenario).items():
        texto = r.get_data(as_text=True).replace(' ', '')
        assert '"casa":9' not in texto and '"casa":7' not in texto, rota


# ---------- Palpites: só até a rodada liberada (item 8) ----------

def _resultado_na_rodada_2(cenario):
    gremio = Jogo.query.filter_by(time_casa='Grêmio').one()
    gremio.data = datetime.now() - timedelta(hours=3)
    db.session.add(Resultado(jogo=gremio, gols_casa_real=9, gols_fora_real=8))
    db.session.commit()


def test_sem_rodada_liberada_nenhum_palpite_aparece(client, cenario):
    """Mesmo com resultado lançado, sem tabela liberada nenhum palpite sai do servidor."""
    dados = client.get(cenario['base'] + '/api/palpites?rodada=1').get_json()
    assert dados['palpitesLiberados'] is False
    assert all(j['revelado'] is False and 'palpites' not in j for j in dados['jogos'])
    for rota, r in todo_json(client, cenario).items():
        texto = r.get_data(as_text=True)
        assert '"palpites":[' not in texto.replace(' ', ''), rota
        assert 'Pedro' not in texto, rota  # palpite de primeiro gol da Ana


def test_rodada_posterior_a_liberada_fica_oculta_mesmo_com_resultado(client, cenario):
    _resultado_na_rodada_2(cenario)
    liberar(client, cenario, cenario['r1'])
    r2 = client.get(cenario['base'] + '/api/palpites?rodada=2').get_json()
    assert r2['palpitesLiberados'] is False and r2['pontosLiberados'] is False
    assert r2['jogos'][0]['golsCasa'] == 9  # o placar do jogo é público...
    assert r2['jogos'][0]['revelado'] is False and 'palpites' not in r2['jogos'][0]  # ...o palpite não
    assert [r['palpitesLiberados'] for r in r2['rodadas']] == [True, False]
    # O palpite 9x8 da Ana na rodada 2 não aparece em resposta nenhuma.
    for rota, r in todo_json(client, cenario).items():
        texto = r.get_data(as_text=True).replace(' ', '')
        assert '"casa":9,"fora":8' not in texto and '"fora":8,"casa":9' not in texto, rota
    # Ao liberar a rodada 2, os palpites dela passam a aparecer.
    liberar(client, cenario, cenario['r2'])
    r2 = client.get(cenario['base'] + '/api/palpites?rodada=2').get_json()
    ana = next(p for p in r2['jogos'][0]['palpites'] if p['nome'] == 'Ana Souza')
    assert (ana['casa'], ana['fora']) == (9, 8)


def test_palpites_nao_sao_lidos_do_banco_para_rodada_nao_liberada(client, cenario, app):
    """A restrição é na consulta: nenhuma linha de palpite da rodada oculta é carregada."""
    from sqlalchemy import event
    _resultado_na_rodada_2(cenario)
    liberar(client, cenario, cenario['r1'])
    cache_publico.invalidar()
    consultas = []
    motor = db.engine
    ouvir = lambda conn, cursor, sql, params, ctx, many: consultas.append(sql)
    event.listen(motor, 'before_cursor_execute', ouvir)
    try:
        client.get(cenario['base'] + '/api/palpites?rodada=2')
    finally:
        event.remove(motor, 'before_cursor_execute', ouvir)
    assert not any('FROM palpite' in sql for sql in consultas)


def test_rodada_padrao_dos_palpites_e_a_ultima_liberada(client, cenario):
    _resultado_na_rodada_2(cenario)
    liberar(client, cenario, cenario['r1'])
    assert client.get(cenario['base'] + '/api/palpites').get_json()['rodada']['numero'] == 1


# ---------- Tabela bloqueada / liberada ----------

def test_tabela_bloqueada_nao_envia_pontos(client, cenario):
    assert client.get(cenario['base'] + '/api/classificacao').get_json() == {'liberada': False}
    assert client.get(cenario['base'] + '/api/classificacao?rodada=1').get_json() == {'liberada': False}
    inicio = client.get(cenario['base'] + '/api/inicio').get_json()
    assert inicio['tabela'] is None and inicio['lideres'] is None
    for rota, r in todo_json(client, cenario).items():
        assert '"pontos"' not in r.get_data(as_text=True), rota


def test_tabela_liberada_ate_rodada(client, cenario):
    resposta = liberar(client, cenario, cenario['r1'])
    assert resposta['rodadaLiberada']['nome'] == '1ª Rodada'
    dados = client.get(cenario['base'] + '/api/classificacao').get_json()
    assert dados['liberada'] is True and dados['ate'] == {'numero': 1, 'nome': '1ª Rodada'}
    # Desistentes ocultos por padrão; Ana: cravada em clássico = 5 pts.
    assert [(i['nome'], i['pontos']) for i in dados['itens']] == [('Ana Souza', 5), ('Responsável', 0)]
    com = client.get(cenario['base'] + '/api/classificacao?desistentes=mostrar').get_json()
    assert {i['nome'] for i in com['itens']} == {'Ana Souza', 'Bia', 'Responsável'}
    # Pontos por jogo aparecem na rodada liberada...
    fla = client.get(cenario['base'] + '/api/palpites?rodada=1').get_json()['jogos'][0]
    assert {p['nome']: p['pontos'] for p in fla['palpites']} == {'Ana Souza': 5, 'Bia': 0, 'Responsável': 0}
    # ...mas não numa rodada posterior à liberada.
    assert client.get(cenario['base'] + '/api/classificacao?rodada=2').status_code == 404
    assert client.get(cenario['base'] + '/api/palpites?rodada=2').get_json()['pontosLiberados'] is False
    # Ocultar de novo some com tudo.
    liberar(client, cenario, None)
    assert client.get(cenario['base'] + '/api/classificacao').get_json() == {'liberada': False}


def test_dashboard_nao_mostra_palpites_faltantes(client, cenario):
    for r in (client.get(cenario['base'] + '/api/inicio'),):
        texto = r.get_data(as_text=True).lower()
        assert 'faltant' not in texto and 'pendenc' not in texto and 'pendent' not in texto


# ---------- Classificação completa, regras, participante, jogos e tabela ----------

def test_classificacao_tem_colunas_completas(client, cenario):
    liberar(client, cenario, cenario['r1'])
    ana = client.get(cenario['base'] + '/api/classificacao').get_json()['itens'][0]
    assert ana['nome'] == 'Ana Souza'
    for campo in ('bonus', 'bonusPrimeiroGol', 'cravadas', 'acertos', 'pontos', 'pontosPalpites', 'variacao', 'ref'):
        assert campo in ana, campo
    assert ana['cravadas'] == 1 and ana['pontos'] == 5


def test_inicio_traz_regras_de_pontuacao(client, cenario):
    regras = client.get(cenario['base'] + '/api/inicio').get_json()['regras']
    assert regras == {'comumExato': 3, 'comumResultado': 1, 'classicoExato': 5, 'classicoResultado': 3,
                      'primeiroGol': 2, 'penaltisExato': 3, 'penaltisVencedor': 1, 'politicaEntrada': cenario['bolao'].politica_entrada_tardia}


def test_detalhe_do_participante(client, cenario):
    lista = client.get(cenario['base'] + '/api/participantes').get_json()['participantes']
    ref = next(p['ref'] for p in lista if p['nome'] == 'Ana Souza')
    # Sem tabela liberada: só nome e status, sem pontos.
    oculto = client.get(f"{cenario['base']}/api/participantes/{ref}")
    assert oculto.status_code == 200 and oculto.get_json()['liberada'] is False
    assert '"pontos"' not in oculto.get_data(as_text=True)
    liberar(client, cenario, cenario['r1'])
    dados = client.get(f"{cenario['base']}/api/participantes/{ref}").get_json()
    assert dados['nome'] == 'Ana Souza' and dados['posicao'] == 1 and dados['pontos'] == 5
    assert [(e['numero'], e['pontos'], e['cravadas']) for e in dados['evolucao']] == [(1, 5, 1)]
    texto = json.dumps(dados)
    assert '@' not in texto and 'paga em dia' not in texto
    assert not re.search(r'"(id|participacaoId|rodadaId|usuarioId)"', texto)


def test_detalhe_do_participante_nao_passa_da_rodada_liberada(client, cenario):
    _resultado_na_rodada_2(cenario)
    liberar(client, cenario, cenario['r1'])
    lista = client.get(cenario['base'] + '/api/participantes').get_json()['participantes']
    ref = next(p['ref'] for p in lista if p['nome'] == 'Ana Souza')
    dados = client.get(f"{cenario['base']}/api/participantes/{ref}").get_json()
    assert [e['numero'] for e in dados['evolucao']] == [1] and dados['pontos'] == 5


def test_referencia_de_participante_invalida_ou_de_link_antigo(client, cenario):
    lista = client.get(cenario['base'] + '/api/participantes').get_json()['participantes']
    ref = lista[0]['ref']
    for ruim in ('0' * 16, 'xyz', str(cenario['ana'].id), ref.upper(), ref + '0'):
        assert client.get(f"{cenario['base']}/api/participantes/{ruim}").status_code == 404, ruim
    entrar(client, cenario['usuario'])
    novo = client.post(f"/interface/api/boloes/{cenario['bolao'].id}/publico/link", json={'acao': 'gerar'}).get_json()
    client.get('/logout')
    base_nova = '/publico/' + novo['link'].rsplit('/', 1)[1]
    assert client.get(f'{base_nova}/api/participantes/{ref}').status_code == 404  # referência antiga não vale


def test_jogos_atrasados_no_publico(client, cenario):
    dados = client.get(cenario['base'] + '/api/jogos').get_json()
    assert dados['rodada']['numero'] == 2 and dados['rodada']['atual'] is True
    assert [(j['casa'], j['rodadaNome']) for j in dados['atrasados']] == [('Santos', '1ª Rodada')]
    assert 'faltantes' not in json.dumps(dados) and 'estado' not in json.dumps(dados)


def test_tabela_do_campeonato_publica(client, cenario, monkeypatch):
    def falsa(**_):
        return {'sucesso': True, 'grupos': [{'nome': 'Série A', 'linhas': [{
            'posicao': 1, 'time_nome': 'Flamengo', 'time_nome_completo': 'CR Flamengo', 'time_sigla': 'FLA',
            'time_id': 1783, 'escudo': None, 'pontos': 70, 'jogos': 30, 'vitorias': 21, 'empates': 7,
            'derrotas': 2, 'gols_pro': 60, 'gols_contra': 20, 'saldo_gols': 40, 'zona': None}]}],
            'legendas': [], 'mata_mata': [{'nome': 'Final', 'jogos': [{'id': 999, 'casa': 'A', 'fora': 'B',
                                                                       'gols_casa': 1, 'gols_fora': 0,
                                                                       'status': 'FINISHED', 'horario': None}]}]}
    monkeypatch.setattr('services.tabela_campeonato.buscar_classificacao', falsa)
    r = client.get(cenario['base'] + '/api/tabela')
    assert r.status_code == 200
    dados = r.get_json()
    assert dados['grupos'][0]['linhas'][0]['time'] == 'Flamengo'
    assert '"id"' not in r.get_data(as_text=True) and 'time_id' not in r.get_data(as_text=True)


# ---------- Segurança ----------

def test_sem_dados_pessoais_nem_ids_internos(client, cenario):
    for rota, r in todo_json(client, cenario).items():
        assert r.status_code == 200, rota
        texto = r.get_data(as_text=True)
        assert '@' not in texto and 'segredo' not in texto and 'paga em dia' not in texto, rota
        assert 'mudou de cidade' not in texto, rota
        assert not re.search(r'"(id|participacaoId|usuarioId|bolaoId|jogoId|rodadaId)"', texto), rota


def test_link_invalido_ou_revogado_da_404_generico(client, cenario):
    for url in ('/publico/nao-existe-esse-codigo', '/publico/x', '/publico/' + 'a' * 22 + '/api/inicio',
                "/publico/abc'%20OR%201=1--aaaaaaaaaa/api/inicio"):
        r = client.get(url)
        assert r.status_code == 404, url
        assert cenario['bolao'].nome not in r.get_data(as_text=True)
    antigo = cenario['base']
    entrar(client, cenario['usuario'])
    novo = client.post(f"/interface/api/boloes/{cenario['bolao'].id}/publico/link", json={'acao': 'gerar'}).get_json()
    client.get('/logout')
    assert client.get(antigo + '/api/inicio').status_code == 404
    assert client.get(antigo).status_code == 404
    assert client.get('/publico/' + novo['link'].rsplit('/', 1)[1] + '/api/inicio').status_code == 200


def test_rotas_publicas_nao_aceitam_gravacao(client, cenario):
    for rota in ('', '/api/inicio', '/api/palpites', '/api/classificacao', '/api/participantes', '/api/tabela',
                 '/api/participantes/' + '0' * 16):
        for metodo in ('post', 'put', 'patch', 'delete'):
            r = getattr(client, metodo)(cenario['base'] + rota, json={'jogos': {}})
            assert r.status_code == 405, (metodo, rota)


def test_link_publico_nao_abre_o_admin(client, cenario):
    client.get(cenario['base'] + '/api/inicio')
    for rota in ('/interface/api/participantes', '/interface/api/palpites', '/interface/api/dashboard',
                 f"/interface/api/boloes/{cenario['bolao'].id}/publico"):
        assert client.get(rota).status_code == 401, rota
    r = client.post('/interface/api/palpites', json={'participacaoId': cenario['ana'].id, 'rodadaId': 1})
    assert r.status_code in (401, 403)
    # Caminhos do admin "dentro" do link não existem.
    for rota in ('/api/../../interface/api/participantes', '/interface/api/participantes', '/admin'):
        assert client.get(cenario['base'] + rota).status_code == 404, rota


def test_publico_nao_cria_sessao_e_tem_cabecalhos(client, cenario):
    r = client.get(cenario['base'] + '/api/inicio')
    assert 'Set-Cookie' not in r.headers
    assert r.headers['X-Robots-Tag'].startswith('noindex')
    assert r.headers['Referrer-Policy'] == 'no-referrer'
    assert 'max-age' in r.headers['Cache-Control']
    pagina = client.get(cenario['base'])
    assert pagina.status_code == 200 and 'Set-Cookie' not in pagina.headers


def test_somente_responsavel_configura_o_link(client, cenario, app):
    outro = Participante.query.filter_by(email='outro@example.com').one()
    entrar(client, outro)
    bolao_id = cenario['bolao'].id
    assert client.get(f'/interface/api/boloes/{bolao_id}/publico').status_code in (403, 404)
    assert client.post(f'/interface/api/boloes/{bolao_id}/publico/link', json={'acao': 'desativar'}).status_code in (403, 404)
    assert client.put(f'/interface/api/boloes/{bolao_id}/publico/tabela', json={'rodadaId': None}).status_code in (403, 404)


def test_desativar_link(client, cenario):
    entrar(client, cenario['usuario'])
    r = client.post(f"/interface/api/boloes/{cenario['bolao'].id}/publico/link", json={'acao': 'desativar'})
    assert r.status_code == 200 and r.get_json()['link'] is None
    client.get('/logout')
    assert client.get(cenario['base'] + '/api/inicio').status_code == 404


def test_rodada_de_outro_campeonato_nao_pode_ser_liberada(client, cenario, gestao):
    _, boloes = gestao
    outra = Rodada(nome='9ª Rodada', campeonato=boloes[1].campeonato)
    db.session.add(outra)
    db.session.commit()
    entrar(client, cenario['usuario'])
    r = client.put(f"/interface/api/boloes/{cenario['bolao'].id}/publico/tabela", json={'rodadaId': outra.id})
    assert r.status_code == 400


def test_numero_de_rodada_invalido(client, cenario):
    for q in ('rodada=99', 'rodada=0', 'rodada=-1', 'rodada=abc'):
        assert client.get(cenario['base'] + '/api/palpites?' + q).status_code == 404, q


# ---------- Cache e limite ----------

def test_cache_atualiza_depois_de_gravar_resultado(client, cenario):
    liberar(client, cenario, cenario['r1'])
    antes = client.get(cenario['base'] + '/api/palpites?rodada=1').get_json()
    assert next(j for j in antes['jogos'] if j['casa'] == 'Santos')['revelado'] is False
    santos = Jogo.query.filter_by(time_casa='Santos').one()
    db.session.add(Resultado(jogo=santos, gols_casa_real=1, gols_fora_real=1))
    db.session.commit()
    depois = client.get(cenario['base'] + '/api/palpites?rodada=1').get_json()
    s = next(j for j in depois['jogos'] if j['casa'] == 'Santos')
    assert s['revelado'] is True and any(p.get('casa') == 7 for p in s['palpites'])


def test_limite_de_requisicoes_nas_rotas_publicas(monkeypatch):
    from app import create_app
    from config import TestingConfig
    from models import Bolao, Campeonato
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_ENABLED', True)
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_STORAGE_URI', 'memory://')
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        dono = Participante(nome='Resp', email='resp@example.com')
        db.session.add(Bolao(nome='Limite', campeonato=Campeonato(nome='C', ano=2026), criador=dono,
                             codigo_publico='codigo-de-teste-limite'))
        db.session.commit()
        cliente = app.test_client()
        codigos = [cliente.get('/publico/codigo-de-teste-limite/api/participantes').status_code for _ in range(91)]
        assert codigos[:90] == [200] * 90 and codigos[90] == 429
        corpo = cliente.get('/publico/codigo-de-teste-limite/api/participantes')
        assert corpo.status_code == 429 and corpo.get_json() == {'erro': 'Muitos acessos em pouco tempo. Aguarde um instante.'}
        db.session.remove()
        db.drop_all()


def test_paginas_carregam_css_e_script_do_build(client, cenario):
    """Com duas entradas no Vite, o CSS fica num pedaço compartilhado: as duas páginas precisam dele."""
    from pathlib import Path
    from flask import current_app
    if not (Path(current_app.static_folder) / 'interface' / '.vite' / 'manifest.json').is_file():
        pytest.skip('Interface não compilada neste ambiente.')
    publica = client.get(cenario['base']).get_data(as_text=True)
    assert re.search(r'/static/interface/assets/[^"]+\.css', publica)
    assert re.search(r'/static/interface/assets/publico-[^"]+\.js', publica)
    entrar(client, cenario['usuario'])
    gestao_html = client.get('/interface/').get_data(as_text=True)
    assert re.search(r'/static/interface/assets/[^"]+\.css', gestao_html)
    assert re.search(r'/static/interface/assets/main-[^"]+\.js', gestao_html)
    assert 'publico-' not in gestao_html.split('<body>')[1]  # a gestão não carrega a página pública
