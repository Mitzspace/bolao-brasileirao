"""Regras de campeonato e rodadas usadas pelas telas atuais e pela nova interface.

Extraído de routes/admin.py sem mudança de comportamento.
"""
import re

from database import db
from models import Rodada
from services.validacao_formularios import inteiro, texto


def validar_campeonato(nome, ano, codigo_api=None):
    """Retorna valores limpos ou lança ValueError com a mensagem para o usuário."""
    nome = texto(nome, 'Nome')
    ano = inteiro(ano, 'Temporada', 1, 9999)
    if codigo_api is not None:
        codigo_api = (codigo_api or 'BSA').strip().upper()
        if not re.fullmatch(r'[A-Z0-9]{1,20}', codigo_api):
            raise ValueError('Código da API: use somente letras e números (ex.: BSA).')
    return nome, ano, codigo_api


def editar_campeonato(camp, nome, ano, codigo_api=None):
    nome, ano, codigo_api = validar_campeonato(nome, ano, codigo_api)
    camp.nome = nome
    camp.ano = ano
    if codigo_api is not None:
        camp.codigo_api = codigo_api
    db.session.commit()
    return camp


def criar_rodada(campeonato_id, nome, aberta=True):
    nome = texto(nome, 'Nome')
    rodada = Rodada(nome=nome, campeonato_id=campeonato_id, aberta=aberta)
    db.session.add(rodada)
    db.session.commit()
    return rodada


def alternar_rodada(rodada):
    rodada.aberta = not rodada.aberta
    db.session.commit()
    return rodada.aberta


def rodada_tem_historico(rodada):
    return bool(rodada.bonus_list or any(jogo.palpites for jogo in rodada.jogos))


def excluir_rodada(rodada):
    """Exclui rodada sem palpites/créditos. Lança ValueError se houver histórico."""
    if rodada_tem_historico(rodada):
        raise ValueError('Esta rodada possui palpites ou créditos históricos e não pode ser excluída.')
    for jogo in rodada.jogos:
        if jogo.resultado:
            db.session.delete(jogo.resultado)
        for palpite in jogo.palpites:
            db.session.delete(palpite)
        db.session.delete(jogo)
    db.session.delete(rodada)
    db.session.commit()
