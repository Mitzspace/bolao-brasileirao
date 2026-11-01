"""Aba Estatísticas da nova interface: possíveis ganhadores, somente leitura."""
from flask import jsonify

from routes.api import api, requer_gestao
from services import cache_publico
from services.contexto_bolao import bolao_atual
from services.estatisticas import possiveis_ganhadores


@api.get('/estatisticas')
@requer_gestao()
def estatisticas():
    bolao = bolao_atual()
    # A simulação é a parte mais pesada da gestão; qualquer gravação invalida o cache.
    dados = cache_publico.obter(('gestao', bolao.id, 'estatisticas'), lambda: possiveis_ganhadores(bolao))
    return jsonify({
        **dados,
        'bolao': {'id': bolao.id, 'nome': bolao.nome, 'campeonato': bolao.campeonato.nome,
                  'ano': bolao.campeonato.ano, 'status': bolao.status},
    })
