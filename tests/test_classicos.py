"""Clássicos marcados automaticamente ao criar jogos (lista em services/classicos.py)."""
import pytest

from database import db
from models import Jogo, Rodada
from services.classicos import CLASSICOS, eh_classico
from tests.test_interface import entrar, gestao  # noqa: F401


def test_lista_tem_16_confrontos_distintos():
    assert len(CLASSICOS) == 16
    assert len({frozenset(par) for par in CLASSICOS}) == 16


@pytest.mark.parametrize('casa, fora', [
    ('SC Corinthians Paulista', 'São Paulo FC'), ('São Paulo FC', 'SC Corinthians Paulista'),
    ('SE Palmeiras', 'Santos FC'), ('CR Vasco da Gama', 'CR Flamengo'),
    ('Grêmio FBPA', 'SC Internacional'), ('CA Mineiro', 'Cruzeiro EC'),
    ('Atlético-MG', 'Cruzeiro'), ('EC Vitória', 'EC Bahia'), ('CA Paranaense', 'Coritiba FBC'),
    ('Athletico-PR', 'Coritiba'), ('Botafogo FR', 'Fluminense FC'),
])
def test_reconhece_nomes_da_api_e_dos_bolões_em_qualquer_mando(casa, fora):
    assert eh_classico(casa, fora)


@pytest.mark.parametrize('casa, fora', [
    ('Remo', 'Bahia'), ('Corinthians', 'Flamengo'), ('Santos', 'Cruzeiro'),
    ('Mirassol', 'Chapecoense AF'), ('Santos', 'Santos'),
])
def test_confrontos_comuns_nao_sao_classicos(casa, fora):
    assert not eh_classico(casa, fora)


def test_cadastro_pela_interface_marca_classico_sozinho_e_edicao_continua_livre(client, gestao):
    usuario, boloes = gestao
    rodada = Rodada(nome='Rodada 1', campeonato=boloes[0].campeonato)
    db.session.add(rodada)
    db.session.commit()
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': boloes[0].id})
    corpo = {'rodadaId': rodada.id, 'data': '', 'classico': False}
    derby = client.post('/interface/api/jogos', json={**corpo, 'casa': 'Palmeiras', 'fora': 'Corinthians'}).get_json()['id']
    comum = client.post('/interface/api/jogos', json={**corpo, 'casa': 'Remo', 'fora': 'Bahia'}).get_json()['id']
    assert db.session.get(Jogo, derby).classico and not db.session.get(Jogo, comum).classico
    # Editar vale o que o responsável marcou: desmarcar um clássico à mão não é desfeito.
    client.put(f'/interface/api/jogos/{derby}', json={**corpo, 'casa': 'Palmeiras', 'fora': 'Corinthians'})
    assert not db.session.get(Jogo, derby).classico


def test_sincronizacao_cria_jogo_ja_marcado_como_classico(app, campeonato_teste):
    from unittest.mock import patch
    from services.sync import sync_jogos
    api = [{'external_id': str(i), 'matchday': 1, 'time_casa': c, 'time_fora': f, 'data': None,
            'finalizado': False, 'gols_casa_real': None, 'gols_fora_real': None}
           for i, (c, f) in enumerate([('SC Corinthians Paulista', 'São Paulo FC'), ('Clube do Remo', 'EC Bahia')], 1)]
    with patch('services.sync.buscar_jogos_football_data', return_value=api):
        sync_jogos('t', campeonato_teste.id, 'BSA', campeonato_completo=True)
    marcados = {j.time_casa: j.classico for j in Jogo.query.all()}
    # A sincronização grava os nomes já normalizados (nome curto do time).
    assert marcados == {'Corinthians': True, 'Remo': False}
