"""Vincula a mensagem revisada ao administrador, bolão, pessoa e rodada."""
from flask import current_app
from itsdangerous import URLSafeTimedSerializer


def assinador():
    return URLSafeTimedSerializer(current_app.secret_key, salt='whatsapp-previa-v1')


def assinatura(texto, autor, bolao, pessoa, rodada):
    return assinador().dumps({'texto': texto, 'autor': autor, 'bolao': bolao,
                             'pessoa': pessoa, 'rodada': rodada})


def ler_assinatura(token, autor, bolao, pessoa, rodada):
    dados = assinador().loads(token, max_age=7200)
    if any(dados.get(k) != v for k, v in {'autor':autor, 'bolao':bolao, 'pessoa':pessoa, 'rodada':rodada}.items()):
        raise ValueError('Mensagem pertence a outro contexto de lançamento.')
    return dados['texto']
