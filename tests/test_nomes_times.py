"""Nomes de times padronizados na importação da API e reconhecidos na mensagem do WhatsApp."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from models import Jogo
from services.parser_whatsapp import ler_mensagem
from services.sync import nome_padrao, sync_jogos


@pytest.mark.parametrize('api, esperado', [
    ('CA Mineiro', 'Atlético-MG'), ('Atlético-MG', 'Atlético-MG'), ('CA Paranaense', 'Athletico-PR'),
    ('SC Corinthians Paulista', 'Corinthians'), ('CR Vasco da Gama', 'Vasco'), ('Grêmio FBPA', 'Grêmio'),
    ('Clube do Remo', 'Remo'), ('RB Bragantino', 'Red Bull Bragantino'), ('EC Vitória', 'Vitória'),
    ('São Paulo FC', 'São Paulo'), ('Coritiba FBC', 'Coritiba'), ('SC Internacional', 'Internacional'),
    ('Time de Outro Campeonato', 'Time de Outro Campeonato'),
])
def test_nome_padrao(api, esperado):
    assert nome_padrao(api) == esperado


def test_importacao_grava_nomes_padronizados(app, campeonato_teste):
    api = [{'external_id': '1', 'matchday': 1, 'time_casa': 'CA Mineiro', 'time_fora': 'SC Corinthians Paulista',
            'data': None, 'finalizado': False, 'gols_casa_real': None, 'gols_fora_real': None}]
    with patch('services.sync.buscar_jogos_football_data', return_value=api):
        sync_jogos('t', campeonato_teste.id, 'BSA', campeonato_completo=True)
    jogo = Jogo.query.filter_by(external_id='1').one()
    assert (jogo.time_casa, jogo.time_fora) == ('Atlético-MG', 'Corinthians')


API_R29 = [(1, 'RB Bragantino', 'Mirassol FC'), (2, 'SC Internacional', 'SC Corinthians Paulista'),
           (3, 'Clube do Remo', 'Grêmio FBPA'), (4, 'EC Vitória', 'Chapecoense AF'),
           (5, 'Botafogo FR', 'CR Vasco da Gama'), (6, 'Cruzeiro EC', 'São Paulo FC'),
           (7, 'Santos FC', 'CR Flamengo'), (8, 'CA Paranaense', 'CA Mineiro'),
           (9, 'Fluminense FC', 'Coritiba FBC'), (10, 'SE Palmeiras', 'EC Bahia')]
MENSAGEM_R29 = """*Rodada-29*

Fluminense 1x1  Coritiba
Botafogo 1 x 1Vasco ★
Santos 1 x 1 Flamengo
Palmeiras 2 x 0 Bahia
Red Bull Bragantino 1 x 1 Mirassol
Cruzeiro 0 x 0 São Paulo
Internacional 1 x 0 Corinthians
Athletico-PR 0 x 1 Atlético-MG
Vitória 1 x 0 Chapecoense
Remo 1 x 1 Grêmio"""


def test_mensagem_com_nomes_curtos_casa_com_jogos_da_api():
    jogos = [SimpleNamespace(id=i, time_casa=c, time_fora=f) for i, c, f in API_R29]
    linhas = ler_mensagem(MENSAGEM_R29, jogos)
    assert [l['jogo_id'] for l in linhas] == [9, 5, 7, 10, 1, 6, 2, 8, 4, 3]
    assert not any('Não reconhecido' in a or 'Ambíguo' in a for l in linhas for a in l['avisos'])
