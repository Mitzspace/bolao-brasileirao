"""Aba Jogos: rodada atual/próxima, navegação entre rodadas, jogos atrasados e horários da API."""
from datetime import datetime

from flask import jsonify, request

from models import Rodada
from routes.api import api, erro, requer_gestao
from routes.api_serializacao import serializar_jogo, texto_data
from services.contexto_bolao import bolao_atual, opcoes_rodadas, ordem_rodada
from services.horarios import atualizar_horarios, token_api, ultima_atualizacao
from services.relogio import agora_brasilia
from services.resumo_boloes import rodadas_de_referencia
from services.estado_rodadas import estados_das_rodadas


def _ordenar_jogos(jogos):
    return sorted(jogos, key=lambda j: (j.data is None, j.data or datetime.min, j.id))


@api.get('/jogos')
@requer_gestao()
def agenda_jogos():
    bolao = bolao_atual()
    campeonato_id = bolao.campeonato_id
    rodadas = [r for r, _ in opcoes_rodadas(campeonato_id)]
    referencia = rodadas_de_referencia({campeonato_id})[campeonato_id]['rodada']

    rodada = referencia
    if request.args.get('rodada_id'):
        rodada_id = request.args.get('rodada_id', type=int)
        rodada = next((r for r in rodadas if r.id == rodada_id), None)
        if rodada is None:
            return erro(404, 'Rodada não encontrada neste bolão.')

    indice = rodadas.index(rodada) if rodada in rodadas else None
    jogos = _ordenar_jogos(rodada.jogos) if rodada else []
    datas = [j.data for j in jogos if j.data]

    # Atrasados: jogos sem resultado de rodadas anteriores à rodada atual.
    atrasados = []
    if referencia:
        for r in rodadas:
            if ordem_rodada(r) >= ordem_rodada(referencia):
                break
            for j in _ordenar_jogos(r.jogos):
                if j.resultado is None:
                    atrasados.append({**serializar_jogo(j, campeonato_id), 'rodadaId': r.id, 'rodadaNome': r.nome})

    estados = estados_das_rodadas(bolao, rodadas)
    atualizado = ultima_atualizacao(campeonato_id)
    return jsonify({
        'agora': agora_brasilia().isoformat(),
        'rodada': {
            'id': rodada.id, 'nome': rodada.nome, 'aberta': bool(rodada.aberta),
            'numero': indice + 1 if indice is not None else None, 'total': len(rodadas),
            'atual': bool(referencia and rodada.id == referencia.id),
            'inicio': min(datas).isoformat() if datas else None,
            'inicioTexto': texto_data(min(datas)) if datas else None,
            'fimTexto': texto_data(max(datas)) if datas else None,
            'semHorario': sum(1 for j in jogos if j.data is None),
            'anteriorId': rodadas[indice - 1].id if indice else None,
            'proximaId': rodadas[indice + 1].id if indice is not None and indice + 1 < len(rodadas) else None,
        } if rodada else None,
        'rodadaAtualId': referencia.id if referencia else None,
        'rodadas': [{'id': r.id, 'numero': i, 'nome': r.nome, **estados[r.id]} for i, r in enumerate(rodadas, 1)],
        'jogos': [serializar_jogo(j, campeonato_id) for j in jogos],
        'atrasados': atrasados,
        'horarios': {
            'fonte': 'football-data.org',
            'configurado': bool(token_api() and bolao.campeonato.codigo_api),
            'ultimaAtualizacao': atualizado.strftime('%d/%m %H:%M') if atualizado else None,
        },
    })


@api.post('/horarios/atualizar')
@requer_gestao()
def atualizar_horarios_api():
    corpo = request.get_json(silent=True) or {}
    resultado = atualizar_horarios(bolao_atual().campeonato, forcar=bool(corpo.get('forcar')))
    return jsonify(resultado)
