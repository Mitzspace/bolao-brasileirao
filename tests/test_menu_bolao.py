from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

import pytest
from flask import g, render_template_string, session, url_for
from sqlalchemy import event

from database import db
from tests.test_seletor_bolao import estrutura, login


class Links(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.urls = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.urls.append(dict(attrs).get('href', ''))


def menu(html):
    return html.split('<header', 1)[1].split('</header>', 1)[0]


@pytest.mark.parametrize('global_admin', [False, True])
def test_sem_selecao_oculta_abas_nos_dois_menus(client, participante_teste, campeonato_teste, global_admin):
    estrutura(participante_teste, campeonato_teste, 'A')
    estrutura(participante_teste, campeonato_teste, 'B')
    participante_teste.admin = global_admin
    participante_teste.admin_global = global_admin
    db.session.commit()
    login(client, participante_teste)
    html = menu(client.get('/boloes').text)
    urls = Links(html).urls
    assert '/boloes' in urls and '/logout' in urls
    assert html.count('Meus bolões') == 2
    assert not any(urlsplit(u).path in {'/', '/ranking', '/tabela', '/jogos', '/meus-palpites', '/admin/'} for u in urls)


def test_visitante_so_tem_navegacao_de_autenticacao(client):
    urls = Links(menu(client.get('/login').text)).urls
    assert set(urls) == {'/login', '/cadastro'}


@pytest.mark.parametrize('papel', ['participante', 'responsavel'])
def test_menu_com_bolao_preserva_contexto_e_permissao(client, participante_teste, campeonato_teste, papel):
    a, part = estrutura(participante_teste, campeonato_teste, 'A')
    b, _ = estrutura(participante_teste, campeonato_teste, 'B')
    part.papel = papel
    db.session.commit()
    login(client, participante_teste)
    html = menu(client.get(f'/ranking?bolao_id={a.id}').text)
    urls = Links(html).urls
    client.get(f'/ranking?bolao_id={b.id}')
    for path in ['/jogos', '/tabela', '/ranking', '/meus-palpites']:
        links = [u for u in urls if urlsplit(u).path == path]
        assert len(links) >= 2  # Desktop e celular.
        assert all(parse_qs(urlsplit(u).query)['bolao_id'] == [str(a.id)] for u in links)
    assert any(urlsplit(u).path == '/admin/' for u in urls) == (papel == 'responsavel')
    assert '/boloes' in urls and '/logout' in urls
    # O link salvo na primeira aba continua apontando para A após usar B.
    destino = next(u for u in urls if urlsplit(u).path == '/meus-palpites')
    assert f'value="{a.id}" aria-current="true"' in client.get(destino).text


def test_context_processor_e_menu_nao_repetem_consultas(app, participante_teste, campeonato_teste):
    a, _ = estrutura(participante_teste, campeonato_teste, 'A')
    with app.test_request_context(f'/ranking?bolao_id={a.id}'):
        session['_user_id'] = str(participante_teste.id)
        g.pop('_login_user', None)
        app.preprocess_request()
        consultas = []
        def contar(conn, cursor, statement, parameters, context, executemany):
            consultas.append(statement)
        event.listen(db.engine, 'before_cursor_execute', contar)
        try:
            for _ in range(2):
                contexto = {}
                app.update_template_context(contexto)
                assert contexto['bolao_atual'].id == a.id
                assert contexto['boloes_disponiveis'][0].id == a.id
                render_template_string('{% include "partials/navbar.html" %}{% include "partials/bolao_selector.html" %}')
            assert consultas == []
            assert url_for('participante.ranking', bolao_id=987) == '/ranking?bolao_id=987'
            assert url_for('participante.escolher_bolao') == '/boloes'
            assert url_for('participante.selecionar_bolao') == '/boloes/selecionar'
            assert 'bolao_id' not in url_for('static', filename='css/ui.css')
        finally:
            event.remove(db.engine, 'before_cursor_execute', contar)


def test_admin_links_e_filtro_mantem_bolao(client, participante_teste, campeonato_teste):
    a, _ = estrutura(participante_teste, campeonato_teste, 'A')
    login(client, participante_teste)
    html = client.get(f'/admin/palpites?bolao_id={a.id}').text
    assert f'name="bolao_id" value="{a.id}"' in html
    links = [u for u in Links(html).urls if urlsplit(u).path.startswith('/admin/')]
    assert links and all(parse_qs(urlsplit(u).query)['bolao_id'] == [str(a.id)] for u in links)
