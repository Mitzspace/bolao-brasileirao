"""Dashboard da nova interface: somente leitura, com os mesmos cálculos das telas atuais."""
from datetime import datetime

from flask import jsonify

from routes.api import api, requer_gestao
from routes.api_serializacao import serializar_item_ranking, serializar_jogo
from services.contexto_bolao import bolao_atual, opcoes_rodadas
from services.ranking import ranking_com_variacao
from services.resumo_boloes import resumos_boloes


@api.get('/dashboard')
@requer_gestao()
def dashboard():
    bolao = bolao_atual()
    resumo = resumos_boloes([bolao])[bolao.id]
    rodada = resumo['rodada']
    opcoes = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    ranking, ultima = ranking_com_variacao(bolao)

    jogos = []
    if rodada:
        ordenados = sorted(rodada.jogos, key=lambda j: (j.data is None, j.data or datetime.min, j.id))
        jogos = [serializar_jogo(j, bolao.campeonato_id) for j in ordenados]

    return jsonify({
        'bolao': {'id': bolao.id, 'nome': bolao.nome, 'chave': bolao.chave,
                  'campeonato': bolao.campeonato.nome, 'ano': bolao.campeonato.ano},
        'participantesAtivos': resumo['ativos'],
        'palpitesFaltantes': resumo['pendencias'],
        'rodada': {
            'id': rodada.id, 'nome': rodada.nome, 'aberta': bool(rodada.aberta),
            'numero': next((i for i, r in enumerate(opcoes, 1) if r.id == rodada.id), None),
            'total': len(opcoes), 'ultima': resumo['ultima'],
        } if rodada else None,
        'jogos': jogos,
        'jogosEncerrados': sum(1 for j in jogos if j['status'] == 'encerrado'),
        'top5': [serializar_item_ranking(i) for i in ranking[:5]],
        'variacaoReferencia': ultima.nome if ultima else None,
    })
