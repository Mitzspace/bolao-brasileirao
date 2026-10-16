"""Arquivos (JS/CSS) de uma entrada do Vite, lidos do manifesto gerado no build.

Com duas entradas (gestão e página pública), o Vite separa o código e o CSS
compartilhados num pedaço comum: o CSS precisa ser buscado também nas dependências.
"""
import json
from pathlib import Path

from flask import current_app, url_for


def assets_da_entrada(entrada):
    manifesto = Path(current_app.static_folder) / 'interface' / '.vite' / 'manifest.json'
    if not manifesto.is_file():
        return None
    itens = json.loads(manifesto.read_text(encoding='utf-8'))
    if entrada not in itens:
        return None
    css, precarregar, vistos = [], [], set()

    def visitar(chave, raiz):
        if chave in vistos or chave not in itens:
            return
        vistos.add(chave)
        item = itens[chave]
        for arquivo in item.get('css', []):
            if arquivo not in css:
                css.append(arquivo)
        if not raiz:
            precarregar.append(item['file'])
        for dependencia in item.get('imports', []):
            visitar(dependencia, False)

    visitar(entrada, True)
    endereco = lambda arquivo: url_for('static', filename='interface/' + arquivo)
    return {'script': endereco(itens[entrada]['file']), 'css': [endereco(c) for c in css],
            'precarregar': [endereco(p) for p in precarregar]}
