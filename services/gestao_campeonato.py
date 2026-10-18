"""Regras de campeonato e rodadas usadas pelas telas atuais e pela nova interface.

Extraído de routes/admin.py sem mudança de comportamento.
"""
import re

from database import db
from models import BonusRodada, Jogo, Palpite, Rodada
from services.competicoes import normalizar_codigo_api
from services.validacao_formularios import inteiro, texto


def validar_campeonato(nome, ano, codigo_api=None):
    """Retorna valores limpos ou lança ValueError com a mensagem para o usuário."""
    nome = texto(nome, 'Nome')
    ano = inteiro(ano, 'Temporada', 1, 9999)
    if codigo_api is not None:
        codigo_api = normalizar_codigo_api(codigo_api or 'BSA')
        if not re.fullmatch(r'[A-Za-z0-9._-]{1,40}', codigo_api):
            raise ValueError('Código da API: use letras, números, ponto ou hífen (ex.: BSA ou conmebol.libertadores).')
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


def rodada_tem_historico(rodada):
    return bool(rodada.bonus_list or any(jogo.palpites for jogo in rodada.jogos))


def rodadas_com_historico(rodada_ids):
    """Mesma regra de rodada_tem_historico para várias rodadas, em 2 consultas."""
    ids = list(rodada_ids)
    if not ids:
        return set()
    com_palpites = db.session.query(Jogo.rodada_id).join(Palpite, Palpite.jogo_id == Jogo.id).filter(
        Jogo.rodada_id.in_(ids)).distinct()
    com_creditos = db.session.query(BonusRodada.rodada_id).filter(BonusRodada.rodada_id.in_(ids)).distinct()
    return {r for (r,) in com_palpites} | {r for (r,) in com_creditos}


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
