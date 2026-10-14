from urllib.parse import parse_qs, urlsplit

import pytest

from database import db
from models import Campeonato, Rodada
from tests.test_seletor_bolao import estrutura, login


def trocar(client, origem, destino, aba, **extra):
    return client.post('/boloes/selecionar', data={
        'bolao_id': destino.id, 'bolao_origem_id': origem.id,
        'aba_origem': aba, **extra})


@pytest.mark.parametrize('aba,path', [
    ('participante.inicio', '/'), ('participante.ranking', '/ranking'),
    ('participante.meus_palpites', '/meus-palpites'), ('participante.tabela', '/tabela'),
    ('participante.listar_jogos', '/jogos'),
    ('admin.dashboard', '/admin/'), ('admin.gerenciar_palpites', '/admin/palpites')])
def test_troca_mantem_aba(client, participante_teste, campeonato_teste, aba, path):
    a, _ = estrutura(participante_teste, campeonato_teste, 'Mesmo nome')
    b, _ = estrutura(participante_teste, campeonato_teste, 'Mesmo nome')
    login(client, participante_teste)
    response = trocar(client, a, b, aba, participante_id=999, campeonato_id=999)
    assert response.status_code == 302
    assert urlsplit(response.location).path == path
    assert parse_qs(urlsplit(response.location).query) == {'bolao_id': [str(b.id)]}


@pytest.mark.parametrize('aba,path', [('participante.listar_jogos', '/jogos/'),
    ('participante.visualizar_rodada', '/rodada/'), ('participante.ver_grade_palpites', '/rodada/')])
def test_rodada_so_e_mantida_no_mesmo_campeonato(client, participante_teste, rodada_teste, aba, path):
    a, _ = estrutura(participante_teste, rodada_teste.campeonato, 'A')
    b, _ = estrutura(participante_teste, rodada_teste.campeonato, 'B')
    outro = Campeonato(nome='Outro', ano=2026)
    c, _ = estrutura(participante_teste, outro, 'C')
    login(client, participante_teste)
    response = trocar(client, a, b, aba, rodada_origem_id=rodada_teste.id)
    esperado = path + str(rodada_teste.id) + ('/palpites' if aba.endswith('ver_grade_palpites') else '')
    assert urlsplit(response.location).path == esperado
    response = trocar(client, a, c, aba, rodada_origem_id=rodada_teste.id)
    assert urlsplit(response.location).path == ('/jogos' if aba.endswith('listar_jogos') else '/')
    assert client.get(response.location).status_code == 200


@pytest.mark.parametrize('aba', ['https://example.com', '//example.com', 'auth.logout',
    'admin.excluir_jogo', 'admin.editar_participante', 'inexistente'])
def test_destino_nao_permitido_cai_no_inicio(client, participante_teste, campeonato_teste, aba):
    a, _ = estrutura(participante_teste, campeonato_teste, 'A')
    b, _ = estrutura(participante_teste, campeonato_teste, 'B')
    login(client, participante_teste)
    assert trocar(client, a, b, aba).location == f'/?bolao_id={b.id}'


def test_admin_sem_permissao_no_destino_cai_no_inicio(client, participante_teste, campeonato_teste):
    a, _ = estrutura(participante_teste, campeonato_teste, 'A')
    b, part = estrutura(participante_teste, campeonato_teste, 'B')
    part.papel = 'participante'
    db.session.commit()
    login(client, participante_teste)
    assert trocar(client, a, b, 'admin.gerenciar_palpites').location == f'/?bolao_id={b.id}'
    part.papel = 'responsavel'
    db.session.commit()
    assert trocar(client, a, b, 'admin.sync').location == f'/?bolao_id={b.id}'
    participante_teste.admin_global = True
    db.session.commit()
    assert trocar(client, a, b, 'admin.sync').location == f'/admin/sync?bolao_id={b.id}'


def test_origem_e_id_de_rodada_sao_validados(client, participante_teste, campeonato_teste):
    a, _ = estrutura(participante_teste, campeonato_teste, 'A')
    b, _ = estrutura(participante_teste, campeonato_teste, 'B')
    login(client, participante_teste)
    assert trocar(client, a, b, 'participante.ranking', bolao_origem_id=999).location == f'/?bolao_id={b.id}'
    assert trocar(client, a, b, 'participante.ver_grade_palpites', rodada_origem_id=999).location == f'/?bolao_id={b.id}'


def test_seletor_unico_no_cabecalho_da_aba(client, participante_teste, campeonato_teste):
    a, _ = estrutura(participante_teste, campeonato_teste, 'Amigos')
    login(client, participante_teste)
    html = client.get('/meus-palpites').text
    assert html.count('id="seletor-bolao"') == 1
    assert 'id="seletor-bolao"' in html.split('</header>')[0]
    assert 'Ver todos os bolões' in html
    assert 'name="aba_origem" value="participante.meus_palpites"' in html
    assert f'name="bolao_origem_id" value="{a.id}"' in html
    assert 'Temporada' not in html.split('<summary')[1].split('</summary>')[0]
