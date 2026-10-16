"""Aba Campeonatos: campeonato do bolão, rodadas e tabela oficial."""
import os

from flask import current_app, g, jsonify, request
from flask_login import current_user

from models import Rodada
from routes.api import api, erro, requer_gestao
from services.classificacao import buscar_classificacao
from services.contexto_bolao import bolao_atual, opcoes_rodadas, validar_rodada
from services.estado_rodadas import estados_das_rodadas
from services.grupos_bolao import campeonatos_do_grupo
from services.escudos import escudo_time
from services.gestao_campeonato import (criar_rodada, editar_campeonato, excluir_rodada, rodada_tem_historico,
                                        rodadas_com_historico)


def _rodada_do_bolao(id):
    rodada = Rodada.query.get_or_404(id)
    validar_rodada(rodada)  # 404 se for de outro campeonato
    return rodada


def _serializar_rodada(rodada, estado, tem_historico=None):
    jogos = rodada.jogos
    com_resultado = sum(1 for j in jogos if j.resultado is not None)
    return {
        'id': rodada.id, 'nome': rodada.nome, 'aberta': bool(rodada.aberta),
        'estado': estado['estado'], 'faltantes': estado['faltantes'],
        'jogos': len(jogos), 'comResultado': com_resultado,
        'podeExcluir': not (rodada_tem_historico(rodada) if tem_historico is None else tem_historico),
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
    historico = rodadas_com_historico(r.id for r in rodadas)
    concluidas = sum(1 for r in rodadas if estados[r.id]['estado'] == 'fechada')
    global_ = bool(current_user.admin_global)
    links = {}
    return jsonify({
        'campeonato': {'id': camp.id, 'nome': camp.nome, 'ano': camp.ano, 'codigoApi': camp.codigo_api or '',
                       'totalRodadas': len(rodadas), 'rodadasConcluidas': concluidas},
        'rodadas': [_serializar_rodada(r, estados[r.id], r.id in historico) for r in rodadas],
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


def _opcional(c, chave, limite=20):
    valor = c.get(chave)
    if valor is None or valor == '':
        return None
    valor = str(valor).strip()
    if len(valor) > limite:
        raise ValueError('Valor muito longo em um dos campos.')
    return valor or None


@api.post('/campeonato/sincronizar')
@requer_gestao()
def sincronizar_campeonato():
    """Ferramentas da football-data.org (só administrador geral), no campeonato do bolão atual.

    jogos: importa/atualiza jogos (rodada ou campeonato completo) e resultados já finalizados;
    informacoes: atualiza horários e resultados dos jogos já cadastrados (não cria jogos);
    resultados: grava os placares finalizados dos jogos ligados à API.
    """
    from urllib.error import HTTPError, URLError
    from services.sync import sync_informacoes_jogos, sync_jogos, sync_resultados
    from services.validacao_formularios import texto
    if not current_user.admin_global:
        return erro(403, 'Disponível só para o administrador geral.')
    c = request.get_json(silent=True)
    c = c if isinstance(c, dict) else {}
    camp = bolao_atual().campeonato
    token = (c.get('token') if isinstance(c.get('token'), str) else '').strip() or os.environ.get('FOOTBALL_DATA_TOKEN')
    if not token:
        return erro(400, 'Informe o token da API ou configure FOOTBALL_DATA_TOKEN.')
    acao = c.get('acao')
    try:
        if acao not in {'jogos', 'informacoes', 'resultados'}:
            raise ValueError('Selecione uma ação de sincronização válida.')
        competicao = texto(_opcional(c, 'competicao') or camp.codigo_api or '', 'Competição', 20).upper()
        temporada = _opcional(c, 'temporada') or (str(camp.ano) if camp.ano else None)
        data_inicio, data_fim = _opcional(c, 'dataInicio'), _opcional(c, 'dataFim')
        completo = c.get('campeonatoCompleto') is True
        rodada_api = _opcional(c, 'rodadaApi')
        nome_rodada = _opcional(c, 'nomeRodada', 100)
        if acao == 'jogos' and not completo and not nome_rodada and not rodada_api:
            raise ValueError('Informe o número da rodada na API, o nome da rodada ou marque o campeonato completo.')
    except ValueError as e:
        return erro(400, str(e))
    try:
        if acao == 'jogos':
            r = sync_jogos(token=token, campeonato_id=camp.id, competicao=competicao,
                           nome_rodada=None if completo else nome_rodada, temporada=temporada,
                           rodada_api=None if completo else rodada_api, data_inicio=data_inicio,
                           data_fim=data_fim, campeonato_completo=completo)
            mensagem = (f"Sincronização concluída: {r['criados']} jogos novos, {r['atualizados']} atualizados, "
                        f"{r['resultados_salvos']} resultados salvos e {r['rodadas_criadas']} rodadas criadas.")
        elif acao == 'informacoes':
            r = sync_informacoes_jogos(token=token, campeonato_id=camp.id, competicao=competicao,
                                       temporada=temporada, data_inicio=data_inicio, data_fim=data_fim)
            mensagem = (f"Informações atualizadas: {r['atualizados']} jogos, {r['horarios_atualizados']} horários, "
                        f"{r['resultados_salvos']} resultados salvos, {r['ignorados']} ignorados.")
            if r.get('nao_casados'):
                mensagem += ' Sem correspondência: ' + '; '.join(r['nao_casados'][:5])
        else:
            r = sync_resultados(token=token, competicao=competicao, temporada=temporada,
                                rodada_api=rodada_api, data_inicio=data_inicio, data_fim=data_fim)
            mensagem = f"Resultados sincronizados: {r['atualizados']} atualizados, {r['ignorados']} ignorados."
    except HTTPError as e:
        return erro(502, f'Erro da API ({e.code}): verifique o token e os parâmetros informados.')
    except URLError:
        return erro(502, 'Não foi possível conectar à API. Tente novamente em instantes.')
    return jsonify({'mensagem': mensagem})
