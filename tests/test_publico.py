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
    return {rota: client.get(c['base'] + rota) for rota in rotas}


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
    jogos = client.get(cenario['base'] + '/api/palpites?rodada=1').get_json()['jogos']
    fla = next(j for j in jogos if j['casa'] == 'Flamengo')
    assert fla['revelado'] is True and (fla['golsCasa'], fla['golsFora']) == (2, 1)
    por_nome = {p['nome']: p for p in fla['palpites']}
    assert por_nome['Ana Souza'] == {'nome': 'Ana Souza', 'status': 'ativo', 'situacao': 'valido',
                                     'casa': 2, 'fora': 1, 'primeiroGol': 'Pedro'}
    assert por_nome['Bia']['casa'] == 0


def test_nenhuma_resposta_publica_contem_palpite_de_jogo_sem_resultado(client, cenario):
    for rota, r in todo_json(client, cenario).items():
        texto = r.get_data(as_text=True).replace(' ', '')
        assert '"casa":9' not in texto and '"casa":7' not in texto, rota


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
    for rota in ('', '/api/inicio', '/api/palpites', '/api/classificacao', '/api/participantes'):
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
