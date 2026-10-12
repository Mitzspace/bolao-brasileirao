import pytest
from database import db
from models import Campeonato, Rodada, Jogo, Palpite
from tests.test_seletor_bolao import estrutura, login
from tests.test_ranking_privacidade import contextos
from tests.test_troca_bolao import trocar


def preparar(client, usuario, campeonato):
    b, p = estrutura(usuario, campeonato, 'Amigos')
    rodadas = []
    for numero in (1, 2, 10):
        r = Rodada(nome=f'{numero}ª Rodada', campeonato=campeonato)
        j = Jogo(rodada=r, time_casa='A', time_fora='B', encerrado=numero == 1)
        db.session.add(j)
        db.session.flush()
        db.session.add(Palpite(participacao=p, jogo=j, gols_casa=numero, gols_fora=0))
        rodadas.append(r)
    db.session.commit()
    login(client, usuario)
    return b, rodadas


def test_padrao_pendente_e_filtro_url(client, participante_teste, campeonato_teste):
    b, rs = preparar(client, participante_teste, campeonato_teste)
    ctx = contextos(client.application, client, '/meus-palpites')
    assert ctx['rodada_selecionada'].id == rs[1].id
    assert ctx['rodada_anterior'] == '1' and ctx['rodada_proxima'] == '10'
    assert [i['palpite'].gols_casa for i in ctx['itens']] == [2]
    for chave, anterior, proxima in [('1', None, '2'), ('10', '2', None)]:
        ctx = contextos(client.application, client, f'/meus-palpites?rodada={chave}')
        assert ctx['rodada_chave'] == chave
        assert ctx['rodada_anterior'] == anterior and ctx['rodada_proxima'] == proxima
        assert len(ctx['itens']) == 1
    for r in rs:
        r.jogos[0].encerrado = True
    db.session.commit()
    assert contextos(client.application, client, '/meus-palpites')['rodada_chave'] == '10'


@pytest.mark.parametrize('valor', ['999', 'abc', '', '1&rodada=2', '-1'])
def test_rodada_invalida_nao_expoe_outro_contexto(client, participante_teste, campeonato_teste, valor):
    preparar(client, participante_teste, campeonato_teste)
    assert client.get('/meus-palpites?rodada=' + valor).status_code == 404


def test_troca_preserva_so_no_mesmo_campeonato(client, participante_teste, campeonato_teste):
    a, _ = preparar(client, participante_teste, campeonato_teste)
    b, _ = estrutura(participante_teste, campeonato_teste, 'B')
    c, _ = estrutura(participante_teste, Campeonato(nome='Outro', ano=2026), 'C')
    login(client, participante_teste)
    assert trocar(client, a, b, 'participante.meus_palpites', rodada_origem='10').location == f'/meus-palpites?bolao_id={b.id}&rodada=10'
    assert trocar(client, a, c, 'participante.meus_palpites', rodada_origem='10').location == f'/meus-palpites?bolao_id={c.id}'
    assert trocar(client, a, b, 'participante.meus_palpites', rodada_origem='999').location == f'/meus-palpites?bolao_id={b.id}'


def test_sem_rodadas_e_sem_palpites(client, participante_teste, campeonato_teste):
    b, _ = estrutura(participante_teste, campeonato_teste, 'Amigos')
    login(client, participante_teste)
    assert 'ainda não tem rodadas' in client.get('/meus-palpites').text
    db.session.add(Rodada(nome='Final', campeonato=campeonato_teste))
    db.session.commit()
    ctx = contextos(client.application, client, '/meus-palpites')
    assert ctx['rodada_chave'].startswith('id-')
    assert not ctx['itens'] and ctx['rodada_anterior'] is None and ctx['rodada_proxima'] is None
    html = client.get('/meus-palpites').text
    assert 'nesta rodada' in html and 'Preencher palpites' in html


def test_numeros_repetidos_recebem_chaves_unicas(client, participante_teste, campeonato_teste):
    estrutura(participante_teste, campeonato_teste, 'Amigos')
    db.session.add_all([Rodada(nome='Grupo A rodada 1', campeonato=campeonato_teste),
                        Rodada(nome='Grupo B rodada 1', campeonato=campeonato_teste)])
    db.session.commit()
    login(client, participante_teste)
    ctx = contextos(client.application, client, '/meus-palpites')
    for r, chave in ctx['opcoes_rodadas']:
        assert chave == f'id-{r.id}'
        assert contextos(client.application, client, f'/meus-palpites?rodada={chave}')['rodada_selecionada'].id == r.id
