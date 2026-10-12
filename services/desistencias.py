"""Planejamento e aplicação transacional; nenhuma escrita antes da confirmação."""
import hashlib
import json
from datetime import timezone, timedelta
from types import SimpleNamespace

from flask import abort
from sqlalchemy.orm import joinedload

from database import db
from models import Jogo, Palpite, agora_utc
from services.auditoria import serializar, valores_participacao, valores_palpite
from services.contexto_bolao import ordem_rodada
from services.elegibilidade import dentro_do_periodo
from services.responsaveis import validar_retirada


def preparar(part, acao, rodada, motivo):
    if acao not in {'registrar', 'corrigir', 'reativar', 'restaurar'}:
        abort(400, description='Ação de desistência inválida.')
    if ((acao == 'registrar' and part.status != 'ativo')
            or (acao in {'corrigir', 'reativar'} and part.status != 'desistente')
            or (acao == 'restaurar' and part.status not in {'ativo', 'desistente'})):
        abort(409, description='O status mudou. Reabra a participação antes de continuar.')
    saida = rodada if acao in {'registrar', 'corrigir'} else (
        part.rodada_desistencia if acao == 'restaurar' else None)
    if acao in {'registrar', 'corrigir'}:
        if rodada is None or rodada.campeonato_id != part.bolao.campeonato_id:
            abort(422, description='Selecione uma rodada deste campeonato.')
        if part.rodada_entrada and ordem_rodada(rodada) < ordem_rodada(part.rodada_entrada):
            abort(422, description='A desistência não pode ser anterior à rodada de entrada.')
        if acao == 'registrar':
            validar_retirada(part)
    palpites = (Palpite.query.filter_by(participacao_id=part.id)
        .options(joinedload(Palpite.jogo).joinedload(Jogo.rodada)).populate_existing().all())
    palpites.sort(key=lambda p: (ordem_rodada(p.jogo.rodada), p.jogo.id))
    posteriores = [p for p in palpites if saida and ordem_rodada(p.jogo.rodada) >= ordem_rodada(saida)]
    restauraveis = [p for p in palpites if p.excluido_por_desistencia and dentro_do_periodo(
        part, p.jogo.rodada, saida=saida, usar_saida_atual=False)]
    fingerprint = hashlib.sha256(serializar({
        'participacao': valores_participacao(part), 'id': part.id, 'acao': acao,
        'rodada': saida.id if saida else None, 'motivo': motivo,
        'palpites': [{'id': p.id, 'valores': valores_palpite(p), 'jogo': p.jogo_id,
                      'rodada': (p.jogo.rodada.id, p.jogo.rodada.nome),
                      'times': (p.jogo.time_casa, p.jogo.time_fora)} for p in palpites],
    }).encode()).hexdigest()
    return SimpleNamespace(acao=acao, rodada=saida, motivo=motivo, posteriores=posteriores,
                           restauraveis=restauraveis, fingerprint=fingerprint)


def aplicar(part, plano, autor_id, restaurar):
    if plano.acao in {'registrar', 'corrigir'}:
        part.status = 'desistente'
        part.rodada_desistencia = plano.rodada
        part.motivo_desistencia = plano.motivo or None
        if plano.acao == 'registrar':
            part.desistencia_registrada_em = agora_utc()
            part.desistencia_registrada_por = autor_id
            part.saiu_em = part.desistencia_registrada_em
    elif plano.acao == 'reativar':
        part.status = 'ativo'
        part.rodada_desistencia = None
        part.motivo_desistencia = None
        part.desistencia_registrada_em = None
        part.desistencia_registrada_por = None
        part.saiu_em = None
        # Reativar a pessoa não concede novamente acesso administrativo.
        part.papel = 'participante'
    for palpite in plano.posteriores:
        palpite.excluido_por_desistencia = True
    if restaurar:
        for palpite in plano.restauraveis:
            palpite.excluido_por_desistencia = False
    db.session.commit()


def historico_visivel(logs, rodadas):
    try:
        from zoneinfo import ZoneInfo
        fuso = ZoneInfo('America/Sao_Paulo')
    except (ImportError, KeyError):
        fuso = timezone(timedelta(hours=-3))
    nomes = {r.id: r.nome for r in rodadas}
    campos = {'nome_exibicao': 'Nome', 'status': 'Status', 'papel': 'Papel',
              'rodada_entrada_id': 'Rodada de entrada', 'rodada_desistencia_id': 'Rodada de desistência',
              'motivo_desistencia': 'Motivo', 'observacao': 'Observação'}
    acoes = {'criacao': 'Cadastro', 'edicao': 'Edição', 'desistencia': 'Desistência',
             'correcao': 'Correção', 'reativacao': 'Reativação', 'status': 'Alteração de status'}
    resultado = []
    for log in logs:
        antes, depois = json.loads(log.valores_anteriores or '{}'), json.loads(log.valores_novos)
        mudancas = []
        for campo, rotulo in campos.items():
            if antes.get(campo) != depois.get(campo):
                valores = [antes.get(campo), depois.get(campo)]
                if campo.startswith('rodada_'):
                    valores = [nomes.get(v, v) for v in valores]
                mudancas.append((rotulo, valores[0], valores[1]))
        resultado.append({'acao': acoes.get(log.acao, 'Alteração'),
            'autor': log.autor.nome if log.autor else 'Autor não informado',
            'quando': log.alterado_em.replace(tzinfo=timezone.utc).astimezone(fuso).strftime('%d/%m/%Y às %H:%M'),
            'mudancas': mudancas})
    return resultado
