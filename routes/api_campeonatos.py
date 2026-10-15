"""Aba Campeonatos: campeonato do bolão, rodadas e tabela oficial."""
import os

from flask import current_app, g, jsonify, request, url_for
from flask_login import current_user

from models import Rodada
from routes.api import api, erro, requer_gestao
from services.classificacao import buscar_classificacao
from services.contexto_bolao import bolao_atual, opcoes_rodadas, validar_rodada
from services.estado_rodadas import estados_das_rodadas
from services.grupos_bolao import campeonatos_do_grupo
from services.escudos import escudo_time
from services.gestao_campeonato import criar_rodada, editar_campeonato, excluir_rodada, rodada_tem_historico


def _rodada_do_bolao(id):
    rodada = Rodada.query.get_or_404(id)
    validar_rodada(rodada)  # 404 se for de outro campeonato
    return rodada


def _serializar_rodada(rodada, estado):
    jogos = rodada.jogos
    com_resultado = sum(1 for j in jogos if j.resultado is not None)
    return {
        'id': rodada.id, 'nome': rodada.nome, 'aberta': bool(rodada.aberta),
        'estado': estado['estado'], 'faltantes': estado['faltantes'],
        'jogos': len(jogos), 'comResultado': com_resultado,
        'podeExcluir': not rodada_tem_historico(rodada),
        'links': {
            'grade': url_for('participante.ver_grade_palpites', id=rodada.id),
            'palpites': url_for('admin.gerenciar_palpites', rodada_id=rodada.id),
        },
    }


def campeonatos_do_bolao(bolao):
    return [{'bolaoId': b.id, 'nome': b.campeonato.nome, 'ano': b.campeonato.ano, 'atual': b.id == bolao.id}
            for b in campeonatos_do_grupo(bolao, g.boloes_disponiveis)]


@api.get('/campeonato')
@requer_gestao()
def ver_campeonato():
    bolao = bolao_atual()
    camp = bolao.campeonato
    rodadas = [r for r, _ in opcoes_rodadas(camp.id)]
    estados = estados_das_rodadas(bolao, rodadas)
    concluidas = sum(1 for r in rodadas if estados[r.id]['estado'] == 'fechada')
    global_ = bool(current_user.admin_global) or current_app.config['FEATURE_PARTICIPANTE_LOGIN']
    links = {'novoJogo': url_for('admin.cadastrar_jogo')}
    if global_:
        links['sync'] = url_for('admin.sync')
        links['importarJogos'] = url_for('admin.importar_jogos')  # importação via API football-data
    return jsonify({
        'campeonato': {'id': camp.id, 'nome': camp.nome, 'ano': camp.ano, 'codigoApi': camp.codigo_api or '',
                       'totalRodadas': len(rodadas), 'rodadasConcluidas': concluidas},
        'rodadas': [_serializar_rodada(r, estados[r.id]) for r in rodadas],
        'campeonatosDoBolao': campeonatos_do_bolao(bolao),
        'adminGlobal': global_,
        'links': links,
    })


@api.put('/campeonato')
@requer_gestao()
def salvar_campeonato():
    corpo = request.get_json(silent=True) or {}
    camp = bolao_atual().campeonato
    try:
        editar_campeonato(camp, corpo.get('nome'), corpo.get('ano'), corpo.get('codigoApi'))
    except ValueError as e:
        return erro(400, str(e))
    return jsonify({'mensagem': f'Campeonato "{camp.nome}" atualizado!'})


@api.post('/rodadas')
@requer_gestao()
def nova_rodada():
    corpo = request.get_json(silent=True) or {}
    try:
        rodada = criar_rodada(bolao_atual().campeonato_id, corpo.get('nome'), bool(corpo.get('aberta', True)))
    except ValueError as e:
        return erro(400, str(e))
    return jsonify({'mensagem': f'Rodada "{rodada.nome}" cadastrada!', 'rodadaId': rodada.id}), 201


@api.delete('/rodadas/<int:id>')
@requer_gestao()
def remover_rodada(id):
    rodada = _rodada_do_bolao(id)
    nome = rodada.nome
    try:
        excluir_rodada(rodada)
    except ValueError as e:
        return erro(409, str(e))
    return jsonify({'mensagem': f'Rodada "{nome}" e todos os seus jogos foram excluídos.'})


@api.get('/tabela')
@requer_gestao()
def tabela_oficial():
    camp = bolao_atual().campeonato
    token = current_app.config.get('FOOTBALL_DATA_TOKEN') or os.environ.get('FOOTBALL_DATA_TOKEN')
    competicao = (camp.codigo_api or 'BSA').strip().upper()
    r = buscar_classificacao(token=token, competicao=competicao,
                             temporada=str(camp.ano) if camp.ano else None, campeonato_id=camp.id)
    zona = lambda z: {'nome': z['nome'], 'cor': z['cor'], 'de': z['faixa'][0], 'ate': z['faixa'][1]} if z else None
    return jsonify({
        'sucesso': bool(r.get('sucesso')),
        'erro': r.get('erro'), 'aviso': r.get('aviso'),
        'fonteCache': bool(r.get('fonte_cache')), 'horarioCache': r.get('horario_cache') or '',
        'competicao': r.get('competicao_nome') or camp.nome,
        'grupos': [{
            'nome': g['nome'],
            'linhas': [{
                'posicao': l['posicao'], 'time': l['time_nome'], 'timeCompleto': l['time_nome_completo'],
                'sigla': l['time_sigla'],
                'escudo': escudo_time(l['time_nome_completo'] or l['time_nome'], l['time_id'], l['escudo'], camp.id),
                'pontos': l['pontos'], 'jogos': l['jogos'], 'vitorias': l['vitorias'], 'empates': l['empates'],
                'derrotas': l['derrotas'], 'golsPro': l['gols_pro'], 'golsContra': l['gols_contra'],
                'saldo': l['saldo_gols'], 'zona': zona(l.get('zona')),
            } for l in g['linhas']],
        } for g in r.get('grupos', [])],
        'legendas': [zona(z) for z in r.get('legendas', [])],
        'mataMata': r.get('mata_mata', []),
    })
