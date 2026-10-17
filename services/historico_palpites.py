"""Histórico de alterações dos palpites de um participante (gaveta da tela de lançamento, só gestão).

Lê o log que já existia (PalpiteLog, gravado por services/auditoria.py a cada criação/alteração)
e o agrupa por lançamento: mesmo autor, origem e rodada em poucos segundos = um item da gaveta.

Origem ("canal"):
- "whatsapp": jogo preenchido pela mensagem colada (log com "canal" ou com o texto original);
- "painel": lançado/alterado na tela por um responsável logado;
- "desconhecida": registros antigos sem autor (importações, scripts) e palpites sem nenhum log.
"""
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import or_, true
from sqlalchemy.orm import joinedload

from models import Jogo, Palpite, PalpiteLog, Participante

FUSO = ZoneInfo('America/Sao_Paulo')
JANELA = timedelta(seconds=10)
SITUACOES = {'valido': 'Válido', 'nao_enviado': 'Não enviou', 'fora_prazo': 'Fora do prazo'}
ACOES = {'criacao': 'Lançou', 'alteracao': 'Alterou', 'apos_desistencia': 'Guardou após desistência',
         'restauracao': 'Restaurou'}
MARCA_WHATSAPP = ('%"canal": "whatsapp"%', '%"texto_original_whatsapp"%')


def _local(dt):
    """Datas do banco são UTC sem fuso; a tela mostra horário de São Paulo."""
    return dt.replace(tzinfo=timezone.utc).astimezone(FUSO) if dt else None


def texto_data(dt, com_ano=True):
    local = _local(dt)
    if local is None:
        return None
    return local.strftime('%d/%m/%Y às %H:%M' if com_ano else '%d/%m às %H:%M')


def _json(texto):
    try:
        return json.loads(texto) if texto else None
    except ValueError:
        return None


def canal_do_log(log, novos):
    if novos and novos.get('canal') in ('painel', 'whatsapp'):
        return novos['canal']
    if novos and novos.get('texto_original_whatsapp'):
        return 'whatsapp'
    # Antes de a origem ser gravada, só o painel lançava com usuário logado.
    return 'painel' if log.alterado_por else 'desconhecida'


def _placar(valores):
    if not valores:
        return None
    situacao = valores.get('situacao') or 'valido'
    if situacao != 'valido':
        return SITUACOES.get(situacao, situacao)
    return f"{valores.get('gols_casa')} × {valores.get('gols_fora')}"


def _detalhes(antes, depois):
    """Mudanças além do placar (primeiro gol, guardado após desistência)."""
    linhas = []
    pg_antes = (antes or {}).get('jogador_primeiro_gol') or None
    pg_depois = (depois or {}).get('jogador_primeiro_gol') or None
    if pg_antes != pg_depois and (pg_antes or pg_depois):
        linhas.append(f"Primeiro gol: {pg_antes or '—'} → {pg_depois or '—'}")
    if antes and bool(antes.get('excluido_por_desistencia')) != bool(depois.get('excluido_por_desistencia')):
        linhas.append('Guardado após desistência' if depois.get('excluido_por_desistencia') else 'Voltou a valer')
    return linhas


def _nome_jogo(jogo):
    return f'{jogo.time_casa} × {jogo.time_fora}'


def ultimo_whatsapp(pessoa):
    """Último lançamento feito pela mensagem do WhatsApp (para o aviso no topo da tela)."""
    log = (PalpiteLog.query.join(Palpite, Palpite.id == PalpiteLog.palpite_id)
           .filter(Palpite.participacao_id == pessoa.id,
                   or_(*[PalpiteLog.valores_novos.like(m) for m in MARCA_WHATSAPP]))
           .options(joinedload(PalpiteLog.palpite).joinedload(Palpite.jogo).joinedload(Jogo.rodada))
           .order_by(PalpiteLog.alterado_em.desc(), PalpiteLog.id.desc()).first())
    if log is None:
        return None
    autor = Participante.query.get(log.alterado_por) if log.alterado_por else None
    return {'quandoTexto': texto_data(log.alterado_em, com_ano=False), 'rodada': log.palpite.jogo.rodada.nome,
            'autor': autor.nome if autor else None}


def historico(pessoa):
    """Itens da gaveta, do mais recente para o mais antigo."""
    logs = (PalpiteLog.query.join(Palpite, Palpite.id == PalpiteLog.palpite_id)
            .filter(Palpite.participacao_id == pessoa.id)
            .options(joinedload(PalpiteLog.palpite).joinedload(Palpite.jogo).joinedload(Jogo.rodada))
            .order_by(PalpiteLog.alterado_em.desc(), PalpiteLog.id.desc()).all())
    ids_autores = {l.alterado_por for l in logs if l.alterado_por}
    autores = {p.id: p.nome for p in Participante.query.filter(Participante.id.in_(ids_autores))} if ids_autores else {}

    itens = []
    for log in logs:
        antes, depois = _json(log.valores_anteriores), _json(log.valores_novos) or {}
        canal = canal_do_log(log, depois)
        jogo = log.palpite.jogo
        mudanca = {'jogo': _nome_jogo(jogo), 'antes': _placar(antes), 'depois': _placar(depois),
                   'detalhes': _detalhes(antes, depois)}
        atual = itens[-1] if itens else None
        mesmo_lote = (atual is not None and atual['_autor'] == log.alterado_por and atual['canal'] == canal
                      and atual['_rodada_id'] == jogo.rodada_id and atual['_acao'] == log.acao
                      and abs(atual['_quando'] - log.alterado_em) <= JANELA)
        if not mesmo_lote:
            atual = {
                '_autor': log.alterado_por, '_rodada_id': jogo.rodada_id, '_acao': log.acao, '_quando': log.alterado_em,
                'quando': _local(log.alterado_em).isoformat(), 'quandoTexto': texto_data(log.alterado_em),
                'autor': autores.get(log.alterado_por) if log.alterado_por else None,
                'canal': canal, 'acao': ACOES.get(log.acao, log.acao), 'rodada': jogo.rodada.nome,
                'recebidoEm': None, 'textoWhatsapp': None, 'mudancas': [],
            }
            itens.append(atual)
        atual['mudancas'].append(mudanca)
        # "Recebido em" antigo (antes de sair da tela) vira informação do lançamento.
        if not atual['recebidoEm'] and depois.get('recebido_em') and (not antes or antes.get('recebido_em') != depois.get('recebido_em')):
            try:
                atual['recebidoEm'] = texto_data(datetime.fromisoformat(depois['recebido_em']))
            except (TypeError, ValueError):
                pass
        if not atual['textoWhatsapp'] and depois.get('texto_original_whatsapp'):
            atual['textoWhatsapp'] = depois['texto_original_whatsapp']

    # Palpites antigos sem nenhum registro no log: origem desconhecida, agrupados por rodada.
    com_log = {l.palpite_id for l in logs}
    sem_log = (Palpite.query.filter(Palpite.participacao_id == pessoa.id, ~Palpite.id.in_(com_log) if com_log else true())
               .options(joinedload(Palpite.jogo).joinedload(Jogo.rodada)).all())
    por_rodada = {}
    for p in sem_log:
        por_rodada.setdefault(p.jogo.rodada_id, []).append(p)
    for palpites in por_rodada.values():
        palpites.sort(key=lambda p: (p.jogo.ordem or 0, p.jogo_id))
        quando = next((p.recebido_em or p.criado_em for p in palpites if p.recebido_em or p.criado_em), None)
        itens.append({
            '_quando': quando, 'quando': _local(quando).isoformat() if quando else None,
            'quandoTexto': texto_data(quando), 'autor': None, 'canal': 'desconhecida',
            'acao': 'Registro antigo, sem histórico', 'rodada': palpites[0].jogo.rodada.nome,
            'recebidoEm': texto_data(palpites[0].recebido_em) if palpites[0].recebido_em else None,
            'textoWhatsapp': None,
            'mudancas': [{'jogo': _nome_jogo(p.jogo), 'antes': None,
                          'depois': _placar({'situacao': p.situacao, 'gols_casa': p.gols_casa, 'gols_fora': p.gols_fora}),
                          'detalhes': [f'Primeiro gol: {p.primeiro_gol}'] if p.primeiro_gol else []} for p in palpites],
        })

    itens.sort(key=lambda i: i['_quando'] or datetime.min, reverse=True)
    return [{k: v for k, v in i.items() if not k.startswith('_')} for i in itens]
