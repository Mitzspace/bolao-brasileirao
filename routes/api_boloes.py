"""Aba Bolões da nova interface: lista, classificação completa e criação de bolão."""
from flask import abort, current_app, flash, g, jsonify, request
from flask_login import current_user

from database import db
from routes.api import api, erro, requer_gestao
from routes.api_serializacao import serializar_item_ranking, serializar_regras
from services.contexto_bolao import lembrar_bolao, opcoes_rodadas
from services.criacao_bolao import (criar_bolao, fontes_de_copia, mensagem_criacao,
                                    pessoas_da_origem, validar_dados)
from services.ranking import calcular_ranking, ranking_com_variacao
from services.regras_pontuacao import aplicar_regras, validar_regras
from services.responsaveis import bloquear_bolao
from services.resumo_boloes import resumos_boloes
from services.textos_whatsapp import texto_classificacao_compartilhar
from services.link_publico import configuracao_publica, definir_tabela_publica, gerar_link, desativar_link


def boloes_geridos():
    """Mesmo filtro da entrada da interface: vínculo ativo de responsável."""
    return [b for b in g.boloes_disponiveis if any(
        p.usuario_id == current_user.id and p.status == 'ativo' and p.papel == 'responsavel'
        for p in b.participacoes)]


def _bolao_gerido(id):
    bolao = next((b for b in boloes_geridos() if b.id == id), None)
    if bolao is None:
        abort(404)
    return bolao


@api.get('/boloes')
@requer_gestao(precisa_bolao=False)
def listar_boloes():
    boloes = boloes_geridos()
    resumos = resumos_boloes(boloes)
    return jsonify({'boloes': [{
        'id': b.id, 'nome': b.nome, 'chave': b.chave, 'grupoId': b.grupo_raiz_id,
        'campeonato': b.campeonato.nome, 'ano': b.campeonato.ano, 'status': b.status,
        'participantesAtivos': resumos[b.id]['ativos'],
        'rodada': resumos[b.id]['rodada'].nome if resumos[b.id]['rodada'] else None,
        'palpitesFaltantes': resumos[b.id]['pendencias'],
    } for b in boloes]})


def ler_regras(dados):
    """Converte o JSON da interface (camelCase) e valida; levanta ValueError."""
    dados = dados if isinstance(dados, dict) else {}
    return validar_regras({'comum_exato': dados.get('comumExato'), 'comum_resultado': dados.get('comumResultado'),
                           'classico_exato': dados.get('classicoExato'),
                           'classico_resultado': dados.get('classicoResultado'),
                           'primeiro_gol': dados.get('primeiroGol')})


@api.put('/boloes/<int:id>/regras')
@requer_gestao(precisa_bolao=False)
def salvar_regras(id):
    """Regras do bolão; valem para todas as rodadas, inclusive as já jogadas."""
    bolao = _bolao_gerido(id)
    try:
        regras = ler_regras(request.get_json(silent=True))
    except ValueError as e:
        return erro(400, str(e))
    bloquear_bolao(bolao.id)  # confirma de novo que é responsável, sob bloqueio
    antes = serializar_regras(bolao)
    aplicar_regras(bolao, regras)
    db.session.commit()
    current_app.logger.info('Regras do bolão %s alteradas por %s: %s -> %s', bolao.id, current_user.id,
                            antes, serializar_regras(bolao))
    return jsonify({'mensagem': 'Regras salvas. A classificação foi recalculada com os novos valores.',
                    'regras': serializar_regras(bolao)})


@api.get('/boloes/<int:id>/classificacao')
@requer_gestao(precisa_bolao=False)
def classificacao_bolao(id):
    """Mesma classificação da tela de ranking: geral (com variação) ou de uma rodada."""
    bolao = _bolao_gerido(id)
    opcoes = opcoes_rodadas(bolao.campeonato_id)
    rodada = None
    if request.args.get('rodada_id'):
        rodada_id = request.args.get('rodada_id', type=int)
        rodada = next((r for r, _ in opcoes if r.id == rodada_id), None)
        if rodada is None:
            abort(404)
    ocultar = request.args.get('ocultar_desistentes') == '1'
    referencia = None
    if rodada:
        ranking = calcular_ranking(bolao, rodada, ocultar)
        for posicao, item in enumerate(ranking, 1):
            item['posicao'] = posicao
    else:
        ranking, ultima = ranking_com_variacao(bolao, ocultar)
        referencia = ultima.nome if ultima else None
    grupo = [b for b in boloes_geridos() if b.grupo_raiz_id == bolao.grupo_raiz_id]
    return jsonify({
        'bolao': {'id': bolao.id, 'nome': bolao.nome, 'chave': bolao.chave,
                  'campeonato': bolao.campeonato.nome, 'ano': bolao.campeonato.ano, 'status': bolao.status},
        'campeonatosDoBolao': [{'bolaoId': b.id, 'nome': b.campeonato.nome, 'ano': b.campeonato.ano}
                               for b in sorted(grupo, key=lambda b: (b.grupo_id is not None, b.id))],
        'rodadas': [{'id': r.id, 'nome': r.nome} for r, _ in opcoes],
        'rodadaId': rodada.id if rodada else None,
        'variacaoReferencia': referencia,
        'ranking': [serializar_item_ranking(i) for i in ranking],
        'textoWhatsapp': texto_classificacao_compartilhar(bolao, ranking, rodada),
        'regras': {**serializar_regras(bolao), 'politicaEntrada': bolao.politica_entrada_tardia},
    })


@api.get('/boloes/fontes')
@requer_gestao(precisa_bolao=False)
def fontes_para_copiar():
    """Bolões de onde dá para copiar nomes; com origem_id, lista as pessoas daquele bolão."""
    fontes = fontes_de_copia(current_user)
    origem = None
    if request.args.get('origem_id'):
        origem = next((b for b in fontes if b.id == request.args.get('origem_id', type=int)), None)
        if origem is None:
            return erro(403)
    return jsonify({
        'fontes': [{'id': b.id, 'nome': b.nome, 'campeonato': b.campeonato.nome, 'ano': b.campeonato.ano}
                   for b in fontes],
        'pessoas': [{'id': p.id, 'nome': p.nome_exibicao, 'status': p.status}
                    for p in pessoas_da_origem(origem, current_user)],
    })


@api.post('/boloes')
@requer_gestao(precisa_bolao=False)
def novo_bolao():
    c = request.get_json(silent=True) or {}
    fontes = fontes_de_copia(current_user)
    origem = None
    if c.get('origemId') not in (None, ''):
        if not isinstance(c['origemId'], int):
            return erro(400)
        origem = next((b for b in fontes if b.id == c['origemId']), None)
        if origem is None:
            return erro(403)
    ids = c.get('participacaoIds') or []
    if not isinstance(ids, list) or any(not isinstance(i, int) or isinstance(i, bool) for i in ids):
        return erro(400)
    pessoas = pessoas_da_origem(origem, current_user)
    selecionados = set(ids)
    if selecionados - {p.id for p in pessoas}:
        return erro(403)
    try:
        def txt(chave):
            return c.get(chave) if isinstance(c.get(chave), str) else None
        ano = c.get('ano') if isinstance(c.get('ano'), (str, int)) and not isinstance(c.get('ano'), bool) else None
        dados = validar_dados(txt('nome'), txt('campeonato'), ano, txt('codigoApi'))
    except ValueError as e:
        return erro(400, str(e))
    regras = None
    if c.get('regras') is not None:
        try:
            regras = ler_regras(c.get('regras'))
        except ValueError as e:
            return erro(400, str(e))
    if origem:
        bloquear_bolao(origem.id)
    novo = criar_bolao(current_user, *dados, pessoas, selecionados, regras)
    lembrar_bolao(novo.id)
    mensagem = mensagem_criacao(selecionados)
    flash(mensagem, 'success')
    return jsonify({'bolaoId': novo.id, 'mensagem': mensagem}), 201


# ---------- Link público de consulta (LINK_PUBLICO.md) ----------

@api.get('/boloes/<int:id>/publico')
@requer_gestao(precisa_bolao=False)
def ver_link_publico(id):
    return jsonify(configuracao_publica(_bolao_gerido(id)))


@api.post('/boloes/<int:id>/publico/link')
@requer_gestao(precisa_bolao=False)
def alterar_link_publico(id):
    bolao = _bolao_gerido(id)
    acao = (request.get_json(silent=True) or {}).get('acao')
    if acao not in ('gerar', 'desativar'):
        return erro(400, 'Ação inválida.')
    bloquear_bolao(bolao.id)
    tinha = bool(bolao.codigo_publico)
    if acao == 'gerar':
        gerar_link(bolao)
        mensagem = ('Novo link gerado. O link anterior parou de funcionar.' if tinha
                    else 'Link público criado. Copie e envie para o grupo.')
    else:
        desativar_link(bolao)
        mensagem = 'Link público desativado. Ninguém mais consegue abrir a página.'
    db.session.commit()
    current_app.logger.info('Link público do bolão %s: %s por %s', bolao.id, acao, current_user.id)
    return jsonify({'mensagem': mensagem, **configuracao_publica(bolao)})


@api.put('/boloes/<int:id>/publico/tabela')
@requer_gestao(precisa_bolao=False)
def alterar_tabela_publica(id):
    bolao = _bolao_gerido(id)
    rodada_id = (request.get_json(silent=True) or {}).get('rodadaId')
    if rodada_id is not None and (not isinstance(rodada_id, int) or isinstance(rodada_id, bool)):
        return erro(400, 'Rodada inválida.')
    bloquear_bolao(bolao.id)
    try:
        rodada = definir_tabela_publica(bolao, rodada_id)
    except ValueError as e:
        db.session.rollback()
        return erro(400, str(e))
    db.session.commit()
    mensagem = (f'Classificação liberada ao público até a {rodada.nome}.' if rodada
                else 'Classificação oculta para o público.')
    return jsonify({'mensagem': mensagem, **configuracao_publica(bolao)})
