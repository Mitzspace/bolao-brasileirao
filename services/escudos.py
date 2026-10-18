"""Resolução única, sem baixar imagens nem consultar a API durante a renderização."""
import json
from pathlib import Path
from urllib.parse import urlparse
from flask import current_app, g, url_for
from config_escudos import ESCUDOS_POR_API_ID, ESCUDOS_POR_NOME, SIGLAS_POR_NOME
from config_selecoes import logo_selecao, sigla_selecao
from services.sync import _normalizar_time


def fonte_segura(valor):
    if not valor:
        return None
    if urlparse(valor).scheme == 'https' and urlparse(valor).netloc:
        return valor
    raiz = Path(current_app.static_folder).resolve()
    arquivo = (raiz / valor).resolve()
    if arquivo.is_relative_to(raiz) and arquivo.is_file():
        return url_for('static', filename=arquivo.relative_to(raiz).as_posix())
    return None


def escudo_time(nome, api_id=None, crest=None, campeonato_id=None):
    normalizado = _normalizar_time(nome)
    if api_id is None and not crest:
        if not hasattr(g, '_escudos_cache'):
            from models import ClassificacaoCache
            g._escudos_cache = {}
            for cache in ClassificacaoCache.query.all():
                try:
                    dados = json.loads(cache.dados_json)
                except (ValueError, TypeError):
                    continue
                for grupo in dados.get('standings', []):
                    for linha in grupo.get('table', []):
                        time = linha.get('team', {})
                        for chave in ('name', 'shortName'):
                            if time.get(chave):
                                g._escudos_cache[cache.campeonato_id, _normalizar_time(time[chave])] = time
        time = g._escudos_cache.get((campeonato_id, normalizado), {})
        api_id, crest = time.get('id'), time.get('crest')
    candidatos = [ESCUDOS_POR_API_ID.get(api_id), ESCUDOS_POR_NOME.get(normalizado), logo_selecao(normalizado)]
    candidatos.sort(key=lambda valor: bool(valor and urlparse(valor).scheme))
    fontes = []
    for valor in candidatos + [crest]:
        fonte = fonte_segura(valor)
        if fonte and fonte not in fontes:
            fontes.append(fonte)
    iniciais = ''.join(p[0] for p in nome.split()[:2]).upper() or '?'
    sigla = SIGLAS_POR_NOME.get(normalizado) or sigla_selecao(normalizado) or (normalizado.replace(' ', '')[:3].upper() or iniciais)
    return {'fontes': fontes, 'iniciais': iniciais, 'sigla': sigla}
