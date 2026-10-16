"""Configuração do link público pelo admin: gerar/regenerar/desativar e liberar a tabela."""
import secrets

from flask import url_for

from models import Bolao
from services.contexto_bolao import opcoes_rodadas


def _novo_codigo():
    while True:
        codigo = secrets.token_urlsafe(16)  # 22 caracteres, 128 bits aleatórios
        if not Bolao.query.filter_by(codigo_publico=codigo).first():
            return codigo


def gerar_link(bolao):
    """Cria o link ou troca o código (o link antigo deixa de funcionar na hora)."""
    bolao.codigo_publico = _novo_codigo()


def desativar_link(bolao):
    bolao.codigo_publico = None


def definir_tabela_publica(bolao, rodada_id):
    """None oculta a classificação; senão libera até a rodada informada (do mesmo campeonato)."""
    if rodada_id is None:
        bolao.rodada_publica_id = None
        return None
    rodada = next((r for r, _ in opcoes_rodadas(bolao.campeonato_id) if r.id == rodada_id), None)
    if rodada is None:
        raise ValueError('Escolha uma rodada deste campeonato.')
    bolao.rodada_publica_id = rodada.id
    return rodada


def configuracao_publica(bolao):
    rodadas = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    resumo = []
    for r in rodadas:
        jogos = r.jogos
        com_resultado = sum(1 for j in jogos if j.resultado is not None)
        resumo.append({'id': r.id, 'nome': r.nome, 'jogos': len(jogos), 'comResultado': com_resultado,
                       'completa': bool(jogos) and com_resultado == len(jogos)})
    # Sugestão: a última rodada com todos os resultados lançados.
    sugerida = next((r for r in reversed(resumo) if r['completa']), None)
    liberada = next((r for r in resumo if r['id'] == bolao.rodada_publica_id), None)
    return {
        'link': url_for('publico.pagina', codigo=bolao.codigo_publico, _external=True) if bolao.codigo_publico else None,
        'rodadaLiberada': {'id': liberada['id'], 'nome': liberada['nome']} if liberada else None,
        'sugerida': {'id': sugerida['id'], 'nome': sugerida['nome']} if sugerida else None,
        'rodadas': resumo,
    }
