"""Ajudas comuns dos testes (sessão e bolão com responsável)."""
from flask import g

from database import db
from models import Bolao, Participacao


def login(client, usuario):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(usuario.id)
        sess['_fresh'] = True
    g.pop('_login_user', None)


def estrutura(usuario, campeonato, nome):
    b = Bolao(nome=nome, campeonato=campeonato, criador=usuario)
    p = Participacao(bolao=b, usuario=usuario, nome_exibicao=nome + ' pessoa', papel='responsavel')
    db.session.add_all([b, p])
    db.session.commit()
    return b, p
