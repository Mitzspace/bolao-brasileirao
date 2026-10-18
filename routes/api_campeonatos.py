"""Aba Campeonatos: campeonato do bolão, rodadas e tabela oficial."""
import json

from flask import g, jsonify, request
from flask_login import current_user

from database import db
from models import Rodada
from routes.api import api, erro, requer_gestao
from services.competicoes import FONTE_API_FOOTBALL, FONTES_API, normalizar_fonte
from services.contexto_bolao import bolao_atual, opcoes_rodadas, validar_rodada
from services.estado_rodadas import estados_das_rodadas
from services.grupos_bolao import campeonatos_do_grupo
from services.tabela_campeonato import dados_tabela
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
                       'fonteApi': normalizar_fonte(camp.fonte_api),
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
    fonte = corpo.get('fonteApi')
    if fonte is not None and fonte not in FONTES_API:
        return erro(400, 'Fonte da API inválida (use football-data ou api-football).')
    try:
        editar_campeonato(camp, corpo.get('nome'), corpo.get('ano'), corpo.get('codigoApi'))
    except ValueError as e:
        return erro(400, str(e))
    if fonte is not None and fonte != camp.fonte_api:
        camp.fonte_api = fonte
        db.session.commit()
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
    return jsonify(dados_tabela(bolao_atual().campeonato))


def _mensagem_http(e, fonte):
    """Mensagem do provedor (ex.: plano sem acesso à competição) para o usuário, sem o token."""
    detalhe = ''
    try:
        corpo = json.loads(e.read() or b'{}')
        if isinstance(corpo, dict):
            detalhe = str(corpo.get('message') or corpo.get('errors') or '')[:300]
    except Exception:
        pass
    nome = FONTES_API[fonte]
    if e.code == 429:
        return f'Limite de consultas da {nome} atingido; tente mais tarde.'
    return f'Erro da {nome} ({e.code}): ' + (detalhe or 'verifique a chave, o código e a temporada.')


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
    """Ferramentas de API (só administrador geral), no campeonato do bolão atual, pelo provedor
    do campeonato (fonte_api): football-data.org ou API-Football (com a chave do servidor).

    jogos: importa/atualiza jogos (rodada ou campeonato completo) e resultados já finalizados;
    informacoes: atualiza horários e resultados dos jogos já cadastrados (não cria jogos);
    resultados: grava os placares finalizados dos jogos ligados à API.
    """
    from urllib.error import HTTPError, URLError
    from flask import current_app
    from services.importador_api_football import ErroApiFootball
    from services.sync import (campeonatos_da_competicao, chave_api, sync_informacoes_jogos, sync_jogos,
                               sync_resultados)
    from services.validacao_formularios import texto
    if not current_user.admin_global:
        return erro(403, 'Disponível só para o administrador geral.')
    c = request.get_json(silent=True)
    c = c if isinstance(c, dict) else {}
    camp = bolao_atual().campeonato
    fonte = normalizar_fonte(camp.fonte_api)
    token = (c.get('token') if isinstance(c.get('token'), str) else '').strip() or chave_api(fonte)
    if not token:
        if fonte == FONTE_API_FOOTBALL:
            return erro(400, 'Configure API_FOOTBALL_KEY no servidor para sincronizar com a API-Football.')
        return erro(400, 'Informe o token da API ou configure FOOTBALL_DATA_TOKEN.')
    acao = c.get('acao')
    try:
        if acao not in {'jogos', 'informacoes', 'resultados'}:
            raise ValueError('Selecione uma ação de sincronização válida.')
        competicao = texto(_opcional(c, 'competicao') or camp.codigo_api or '', 'Competição', 20).strip().upper()
        temporada = _opcional(c, 'temporada') or (str(camp.ano) if camp.ano else None)
        data_inicio, data_fim = _opcional(c, 'dataInicio'), _opcional(c, 'dataFim')
        completo = c.get('campeonatoCompleto') is True
        rodada_api = _opcional(c, 'rodadaApi')
        nome_rodada = _opcional(c, 'nomeRodada', 100)
        if acao == 'jogos' and not completo and not nome_rodada and not rodada_api:
            raise ValueError('Informe o número da rodada na API, o nome da rodada ou marque o campeonato completo.')
    except ValueError as e:
        return erro(400, str(e))
    aplicados = 0
    try:
        if acao == 'jogos':
            r = sync_jogos(token=token, campeonato_id=camp.id, competicao=competicao,
                           nome_rodada=None if completo else nome_rodada, temporada=temporada,
                           rodada_api=None if completo else rodada_api, data_inicio=data_inicio,
                           data_fim=data_fim, campeonato_completo=completo, fonte_api=fonte)
            mensagem = (f"Sincronização concluída: {r['criados']} jogos novos, {r['atualizados']} atualizados, "
                        f"{r['resultados_salvos']} resultados salvos e {r['rodadas_criadas']} rodadas criadas.")
        elif acao == 'informacoes':
            if fonte == FONTE_API_FOOTBALL:
                from services.importador_api_football import buscar_jogos_api_football
                jogos_api = buscar_jogos_api_football(chave=token, liga=competicao, temporada=temporada,
                                                      data_inicio=data_inicio, data_fim=data_fim)
            else:
                from services.importador_jogos import buscar_jogos_football_data
                jogos_api = buscar_jogos_football_data(token=token, competicao=competicao, temporada=temporada,
                                                       data_inicio=data_inicio, data_fim=data_fim)
            r = sync_informacoes_jogos(token=token, campeonato_id=camp.id, competicao=competicao,
                                       temporada=temporada, data_inicio=data_inicio, data_fim=data_fim,
                                       jogos_api=jogos_api, fonte_api=fonte)
            # A mesma resposta atualiza os outros bolões do provedor/competição/temporada, sem nova chamada.
            mesma_competicao = ((camp.codigo_api or '').strip().upper() == competicao
                                and temporada == (str(camp.ano) if camp.ano else None))
            irmaos = [x.id for x in campeonatos_da_competicao(competicao, camp.ano, fonte)
                      if x.id != camp.id] if mesma_competicao else []
            for irmao_id in irmaos:
                try:
                    sync_informacoes_jogos(token=token, campeonato_id=irmao_id, competicao=competicao,
                                           temporada=temporada, data_inicio=data_inicio, data_fim=data_fim,
                                           jogos_api=jogos_api, fonte_api=fonte)
                    aplicados += 1
                except Exception:
                    db.session.rollback()
                    current_app.logger.exception('Falha ao aplicar a sincronização no campeonato %s', irmao_id)
            mensagem = (f"Informações atualizadas: {r['atualizados']} jogos, {r['horarios_atualizados']} horários, "
                        f"{r['resultados_salvos']} resultados salvos, {r['ignorados']} ignorados.")
            if aplicados:
                mensagem += f" Também aplicado a {aplicados} outro(s) bolão(ões) da mesma competição."
            if r.get('nao_casados'):
                mensagem += ' Sem correspondência: ' + '; '.join(r['nao_casados'][:5])
        else:
            r = sync_resultados(token=token, competicao=competicao, temporada=temporada,
                                rodada_api=rodada_api, data_inicio=data_inicio, data_fim=data_fim,
                                fonte_api=fonte)
            mensagem = f"Resultados sincronizados: {r['atualizados']} atualizados, {r['ignorados']} ignorados."
    except ErroApiFootball as e:  # plano/temporada, chave inválida, limite diário...
        db.session.rollback()
        return erro(502, str(e))
    except HTTPError as e:
        db.session.rollback()
        return erro(502, _mensagem_http(e, fonte))
    except URLError:
        db.session.rollback()
        return erro(502, 'Não foi possível conectar à API. Tente novamente em instantes.')
    return jsonify({'mensagem': mensagem, 'outrosCampeonatos': aplicados})
