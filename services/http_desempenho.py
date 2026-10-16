"""Compressão gzip e cache do navegador, sem dependências novas.

- JSON da API, HTML e os arquivos JS/CSS da interface saem comprimidos quando o
  navegador aceita gzip (o JS de ~350 KB cai para ~100 KB).
- Arquivos da interface têm o hash no nome (main-XXXX.js): ficam guardados no
  navegador por 1 ano e só são baixados de novo quando um deploy muda o arquivo.
- Escudos e ícones da aba ficam guardados por 7 dias.
- A versão comprimida de cada arquivo estático é guardada em memória, para não
  recomprimir a cada acesso (o processador do Render Free é pequeno).
"""
import gzip
import threading

from flask import request

TIPOS_COMPRIMIVEIS = {
    'application/json', 'text/html', 'text/css', 'application/javascript',
    'text/javascript', 'image/svg+xml', 'text/plain',
}
TAMANHO_MINIMO = 1024
NIVEL = 6
CACHE_ASSETS = 'public, max-age=31536000, immutable'
CACHE_ESCUDOS = 'public, max-age=604800'

_estaticos_comprimidos = {}
_trava = threading.Lock()
_LIMITE_CACHE = 64


def _aceita_gzip():
    return 'gzip' in request.headers.get('Accept-Encoding', '').lower()


def _comprimir(corpo):
    return gzip.compress(corpo, compresslevel=NIVEL, mtime=0)


def _comprimir_estatico(chave, corpo):
    with _trava:
        pronto = _estaticos_comprimidos.get(chave)
    if pronto is None:
        pronto = _comprimir(corpo)
        with _trava:
            if len(_estaticos_comprimidos) >= _LIMITE_CACHE:
                _estaticos_comprimidos.clear()
            _estaticos_comprimidos[chave] = pronto
    return pronto


def cabecalhos_cache(response):
    caminho = request.path
    if response.status_code in (200, 304):
        if caminho.startswith('/static/interface/assets/'):
            response.headers['Cache-Control'] = CACHE_ASSETS
        elif caminho.startswith(('/static/escudos/', '/static/icones/')):
            response.headers['Cache-Control'] = CACHE_ESCUDOS
    return response


def comprimir_resposta(response):
    if (response.status_code != 200 or response.mimetype not in TIPOS_COMPRIMIVEIS
            or 'Content-Encoding' in response.headers or response.is_streamed and not response.direct_passthrough):
        return response
    response.vary.add('Accept-Encoding')
    if not _aceita_gzip():
        return response
    estatico = request.path.startswith('/static/')
    if response.direct_passthrough:
        # Arquivos estáticos: o Flask entrega o arquivo direto; lemos para comprimir.
        response.direct_passthrough = False
    corpo = response.get_data()
    if len(corpo) < TAMANHO_MINIMO:
        return response
    if estatico:
        chave = (request.path, response.get_etag()[0], len(corpo))
        comprimido = _comprimir_estatico(chave, corpo)
    else:
        comprimido = _comprimir(corpo)
    response.set_data(comprimido)
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = str(len(comprimido))
    return response


def registrar(app):
    app.after_request(cabecalhos_cache)
    app.after_request(comprimir_resposta)
