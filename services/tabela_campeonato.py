"""Tabela (classificação) do campeonato na football-data.org ou na ESPN, no formato da nova interface.

Usada pela aba Jogos do admin (/interface/api/tabela) e pelo link público
(/publico/<código>/api/tabela). O serviço services/classificacao.py guarda a
resposta da API no banco por 15 minutos, então as duas telas compartilham o cache.
"""
import os

from flask import current_app

from services.classificacao import buscar_classificacao
from services.escudos import escudo_time
from services.competicoes import FONTE_ESPN, FONTE_FOOTBALL_DATA, FONTES_API, normalizar_fonte


def _zona(z):
    return {'nome': z['nome'], 'cor': z['cor'], 'de': z['faixa'][0], 'ate': z['faixa'][1]} if z else None


def _sem_tabela(campeonato, erro):
    return {
        'sucesso': False, 'erro': erro,
        'aviso': None, 'fonteCache': False, 'horarioCache': '',
        'competicao': campeonato.nome, 'grupos': [], 'legendas': [], 'mataMata': [],
    }


def dados_tabela(campeonato, publico=False):
    """Tabela do campeonato. publico=True tira ids da API externa dos jogos de mata-mata."""
    fonte = normalizar_fonte(campeonato.fonte_api)
    temporada = str(campeonato.ano) if campeonato.ano else None
    if fonte == FONTE_ESPN:
        if not campeonato.codigo_api or not temporada:
            return _sem_tabela(campeonato, 'Informe o código da liga e a temporada para ver a tabela da ESPN.')
        r = buscar_classificacao(competicao=campeonato.codigo_api.strip().casefold(), temporada=temporada,
                                 campeonato_id=campeonato.id, fonte_api=FONTE_ESPN)
        if r.get('sucesso') and not r.get('grupos'):
            return _sem_tabela(campeonato, f'{campeonato.nome} não tem fase de classificação; '
                                           'os confrontos estão na aba Jogos.')
    elif fonte != FONTE_FOOTBALL_DATA:
        return _sem_tabela(campeonato, f'A tabela oficial da {FONTES_API[fonte]} ainda não está disponível. '
                                       'Os jogos e resultados podem ser consultados na aba Jogos.')
    else:
        token = current_app.config.get('FOOTBALL_DATA_TOKEN') or os.environ.get('FOOTBALL_DATA_TOKEN')
        competicao = (campeonato.codigo_api or 'BSA').strip().upper()
        r = buscar_classificacao(token=token, competicao=competicao, temporada=temporada,
                                 campeonato_id=campeonato.id)
    mata_mata = r.get('mata_mata', [])
    if publico:
        mata_mata = [{**fase, 'jogos': [{k: v for k, v in j.items() if k != 'id'} for j in fase.get('jogos', [])]}
                     for fase in mata_mata]
    return {
        'sucesso': bool(r.get('sucesso')),
        'erro': r.get('erro'), 'aviso': r.get('aviso'),
        'fonteCache': bool(r.get('fonte_cache')), 'horarioCache': r.get('horario_cache') or '',
        'competicao': r.get('competicao_nome') or campeonato.nome,
        'grupos': [{
            'nome': g['nome'],
            'linhas': [{
                'posicao': l['posicao'], 'time': l['time_nome'], 'timeCompleto': l['time_nome_completo'],
                'sigla': l['time_sigla'],
                'escudo': escudo_time(l['time_nome_completo'] or l['time_nome'], l['time_id'], l['escudo'],
                                      campeonato.id),
                'pontos': l['pontos'], 'jogos': l['jogos'], 'vitorias': l['vitorias'], 'empates': l['empates'],
                'derrotas': l['derrotas'], 'golsPro': l['gols_pro'], 'golsContra': l['gols_contra'],
                'saldo': l['saldo_gols'], 'zona': _zona(l.get('zona')),
            } for l in g['linhas']],
        } for g in r.get('grupos', [])],
        'legendas': [_zona(z) for z in r.get('legendas', [])],
        'mataMata': mata_mata,
    }
