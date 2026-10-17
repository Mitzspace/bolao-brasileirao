"""Modelo de palpites para o WhatsApp: formato, jogos iniciados e ida e volta pelo leitor de mensagens."""
import re
from datetime import datetime, timedelta

from database import db
from models import Jogo, Rodada
from services.modelo_palpites import montar_modelo, texto_prazo
from services.parser_whatsapp import ler_mensagem, rodadas_informadas
from services.relogio import agora_brasilia
from tests.test_interface import entrar, gestao  # noqa: F401


def rodada_com_jogos(bolao, nome='Rodada 30', inicio=None):
    inicio = inicio or datetime(2030, 10, 19, 16, 0)
    r = Rodada(nome=nome, campeonato=bolao.campeonato)
    jogos = [Jogo(time_casa='Flamengo', time_fora='Fluminense', rodada=r, classico=True, ordem=1, data=inicio + timedelta(hours=2)),
             Jogo(time_casa='Vasco', time_fora='Remo', rodada=r, ordem=2, data=inicio),
             Jogo(time_casa='Palmeiras', time_fora='Corinthians', rodada=r, classico=True, ordem=3, data=inicio + timedelta(days=1)),
             Jogo(time_casa='Atlético-MG', time_fora='Coritiba', rodada=r, ordem=4)]
    db.session.add_all([r, *jogos])
    db.session.commit()
    return r, jogos


def test_formato_do_modelo_e_prazo(gestao):
    r, _ = rodada_com_jogos(gestao[1][0])
    m = montar_modelo(r, agora=datetime(2030, 10, 1))
    assert m['texto'].splitlines() == ['*Rodada-30*', '', 'Flamengo x Fluminense ★', 'Vasco x Remo',
                                       'Palmeiras x Corinthians ★', 'Atlético-MG x Coritiba']
    assert m['prazo'] == 'Palpites até sáb 19/10, 16h'
    assert (m['incluidos'], m['omitidos']) == (4, 0)


def test_texto_prazo_com_minutos():
    assert texto_prazo(datetime(2030, 10, 19, 18, 30)) == 'Palpites até sáb 19/10, 18h30'


def test_jogos_iniciados_ficam_de_fora_e_sao_contados(gestao):
    r, jogos = rodada_com_jogos(gestao[1][0])
    jogos[1].encerrado = True  # Vasco x Remo
    db.session.commit()
    m = montar_modelo(r, agora=datetime(2030, 10, 19, 17, 0))  # Flamengo x Flu (18h) ainda não começou
    assert 'Vasco' not in m['texto'] and 'Flamengo x Fluminense ★' in m['texto']
    assert (m['incluidos'], m['omitidos']) == (3, 1)
    assert m['prazo'] == 'Palpites até sáb 19/10, 18h'
    tudo = montar_modelo(r, agora=datetime(2031, 1, 1))  # só o jogo sem data continua aberto
    assert tudo['texto'].splitlines()[-1] == 'Atlético-MG x Coritiba' and tudo['omitidos'] == 3 and tudo['prazo'] is None
    nada = montar_modelo(Rodada(nome='Rodada 9', jogos=[]), agora=agora_brasilia())
    assert nada['texto'] == '' and nada['incluidos'] == 0


def test_ida_e_volta_todos_os_jogos_reconhecidos_sem_avisos(gestao):
    r, jogos = rodada_com_jogos(gestao[1][0])
    modelo = montar_modelo(r, agora=datetime(2030, 10, 1))['texto']
    preenchido = '\n'.join(
        re.sub(r'^(.+?) x (.+?)( ★)?$', lambda m: f'{m[1]} {i % 3} x {i % 2} {m[2]}' + (' ★ Gabigol' if m[3] else ''), linha)
        if ' x ' in linha else linha for i, linha in enumerate(modelo.splitlines()))
    assert rodadas_informadas(preenchido) == {30}
    linhas = ler_mensagem(preenchido, list(r.jogos))
    assert [l['jogo_id'] for l in linhas] == [j.id for j in r.jogos]
    assert not any(l['avisos'] for l in linhas)
    assert [l['primeiro_gol'] for l in linhas] == ['Gabigol', '', 'Gabigol', '']


def test_rota_do_modelo_so_para_o_responsavel_do_bolao(client, gestao):
    usuario, boloes = gestao
    r, _ = rodada_com_jogos(boloes[0], inicio=agora_brasilia() + timedelta(days=3))
    alheia, _ = rodada_com_jogos(boloes[2])
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': boloes[0].id})
    dados = client.get(f'/interface/api/rodadas/{r.id}/modelo-palpites').get_json()
    assert dados['rodada'] == 'Rodada 30' and dados['texto'].startswith('*Rodada-30*') and dados['prazo'].startswith('Palpites até')
    assert client.get(f'/interface/api/rodadas/{alheia.id}/modelo-palpites').status_code == 404
