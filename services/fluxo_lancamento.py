"""Navegação por rodada e fila de pendências, sem alterar palpites."""
from flask import session
from flask_login import current_user
from services.resumo_boloes import participantes_pendentes, rodadas_de_referencia


def chave_memoria(bolao):
    return f'{current_user.id}:{bolao.id}'


def lembrar_rodada(bolao, rodada):
    memoria = dict(session.get('rodadas_lancamento', {}))
    chave = chave_memoria(bolao)
    memoria.pop(chave, None)
    memoria[chave] = rodada.id
    session['rodadas_lancamento'] = dict(list(memoria.items())[-30:])


def rodada_padrao(bolao, rodadas):
    lembrada = session.get('rodadas_lancamento', {}).get(chave_memoria(bolao))
    return next((r for r in rodadas if r.id == lembrada), None) or rodadas_de_referencia(
        {bolao.campeonato_id})[bolao.campeonato_id]['rodada']


def vizinhos(itens, selecionado):
    ids = [p.id for p in itens]
    if selecionado not in ids:
        return None, None
    indice = ids.index(selecionado)
    return (ids[indice - 1] if indice else None,
            ids[indice + 1] if indice + 1 < len(ids) else None)


def proximo_pendente(bolao, rodada, atual, pessoas):
    pendentes = participantes_pendentes(bolao, rodada)
    ids = {p['participacao'].id for p in pendentes}
    ordem = [p.id for p in pessoas]
    indice = ordem.index(atual) if atual in ordem else -1
    fila = ordem[indice + 1:] + ordem[:indice + 1]
    return next((id for id in fila if id in ids), None)
