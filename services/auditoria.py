"""Integra os gravadores legados à participação e ao log na mesma transação."""
import json
from datetime import datetime
from services.relogio import agora_brasilia
from flask import has_request_context, request
from flask_login import current_user
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from models import (Bolao, Participacao, Participante, Jogo, Resultado,
                    Palpite, PalpiteLog, ParticipacaoLog, BonusRodada, Rodada, agora_utc)


def valores_palpite(palpite):
    return {campo: getattr(palpite, campo) for campo in (
        "participacao_id", "gols_casa", "gols_fora", "penaltis_casa", "penaltis_fora", "jogador_primeiro_gol",
        "origem", "lancado_por", "recebido_em", "lancado_apos_inicio", "auditoria_legada",
        "excluido_por_desistencia", "situacao")}


def serializar(valores):
    return json.dumps(valores, ensure_ascii=False, sort_keys=True,
                      default=lambda v: v.isoformat() if isinstance(v, datetime) else str(v))


def participacao_legada(session, participante_id, campeonato):
    boloes = session.query(Bolao).filter_by(campeonato_id=campeonato.id).all()
    boloes += [b for b in session.new if isinstance(b, Bolao) and b.campeonato is campeonato]
    if len(boloes) > 1:
        raise ValueError("Informe a participação explicitamente: há mais de um bolão neste campeonato.")
    pessoa = session.get(Participante, participante_id)
    if pessoa is None:
        raise ValueError("Participante legado inexistente.")
    if not boloes:
        criador = session.query(Participante).filter_by(admin_global=True).first() or pessoa
        bolao = Bolao(nome=campeonato.nome, campeonato=campeonato, criador=criador)
        session.add(bolao)
    else:
        bolao = boloes[0]
    part = next((p for p in session.new if isinstance(p, Participacao)
                 and p.bolao is bolao and p.participante_legado_id == participante_id), None)
    if part is None and bolao.id:
        part = session.query(Participacao).filter_by(bolao_id=bolao.id, participante_legado_id=participante_id).first()
    if part is None:
        part = Participacao(bolao=bolao, participante_legado_id=participante_id,
            usuario=pessoa if pessoa.admin and pessoa.conta_ativa else None,
            nome_exibicao=pessoa.nome, papel="responsavel" if pessoa.admin else "participante")
        session.add(part)
    return part


@event.listens_for(Session, "before_flush")
def auditar(session, flush_context, instances):
    actor = current_user.id if has_request_context() and current_user.is_authenticated else None
    for obj in list(session.deleted):
        if isinstance(obj, (Participante, Participacao, Palpite, PalpiteLog, ParticipacaoLog)):
            raise ValueError("Histórico preservado: altere o status em vez de excluir pessoas ou palpites.")
    for obj in list(session.dirty):
        if isinstance(obj, (PalpiteLog, ParticipacaoLog)) and session.is_modified(obj, include_collections=False):
            raise ValueError("Logs são imutáveis.")
    for obj in list(session.new) + list(session.dirty):
        if isinstance(obj, Jogo):
            obj._especial_legado = bool(obj.classico)
            if inspect(obj).attrs.primeiro_marcador.history.has_changes() and obj.resultado:
                obj.resultado.primeiro_gol_real = obj.primeiro_marcador
        if isinstance(obj, Resultado) and inspect(obj).attrs.primeiro_gol_real.history.has_changes():
            jogo = obj.jogo or session.get(Jogo, obj.jogo_id)
            if jogo:
                jogo.primeiro_marcador = obj.primeiro_gol_real
    for obj in list(session.new) + list(session.dirty):
        if not isinstance(obj, (Palpite, BonusRodada)):
            continue
        if not obj.participacao and not obj.participacao_id:
            jogo = (obj.jogo or session.get(Jogo, obj.jogo_id)) if isinstance(obj, Palpite) else None
            rodada = jogo.rodada if jogo else obj.rodada
            obj.participacao = participacao_legada(session, obj.participante_id, rodada.campeonato)
        if isinstance(obj, BonusRodada):
            continue
        part = obj.participacao or session.get(Participacao, obj.participacao_id)
        jogo = obj.jogo or session.get(Jogo, obj.jogo_id)
        if part.bolao.campeonato_id and part.bolao.campeonato_id != jogo.rodada.campeonato_id:
            raise ValueError("O jogo não pertence ao campeonato do bolão.")
        if obj.participante_id and part.participante_legado_id != obj.participante_id:
            raise ValueError("Participação incompatível com a identidade legada.")
        novo = obj in session.new
        if not novo and not session.is_modified(obj, include_collections=False):
            continue
        altera_placar = novo or any(inspect(obj).attrs[c].history.has_changes()
            for c in ('gols_casa', 'gols_fora', 'penaltis_casa', 'penaltis_fora', 'jogador_primeiro_gol', 'situacao'))
        from services.elegibilidade import dentro_do_periodo
        if altera_placar and (not dentro_do_periodo(part, jogo.rodada) or obj.excluido_por_desistencia):
            raise ValueError('Palpite fora do período de participação ou guardado após desistência; revise a participação primeiro.')
        anterior = None
        if not novo:
            row = session.connection().execute(Palpite.__table__.select().where(Palpite.id == obj.id)).mappings().one()
            anterior = dict(row)
            anterior["jogador_primeiro_gol"] = anterior.pop("primeiro_gol")
            anterior = {k: anterior[k] for k in valores_palpite(obj)}
        agora = agora_utc()
        if novo:
            obj.criado_em = agora
            obj.lancado_por = actor
            obj.origem = obj.origem or ("proprio" if actor and actor == part.usuario_id and request.blueprint != "admin" else "responsavel")
            obj.auditoria_legada = False
        obj.atualizado_em = agora
        if altera_placar:
            obj.lancado_apos_inicio = bool(jogo.data and agora_brasilia() >= jogo.data)
        if part.id:
            obj.participacao_id = part.id
        acao = "criacao" if novo else "alteracao"
        if not novo and inspect(obj).attrs.excluido_por_desistencia.history.has_changes():
            acao = 'apos_desistencia' if obj.excluido_por_desistencia else 'restauracao'
        # Origem do lançamento ("canal"): definida por quem grava (painel ou WhatsApp); sem isso,
        # uma requisição com usuário logado é o painel e o resto (scripts, importações) fica sem origem.
        canal = getattr(obj, '_canal', None) or ('painel' if actor and has_request_context() else None)
        extras = {**({'texto_original_whatsapp': obj._texto_original} if getattr(obj, '_texto_original', None) else {}),
                  **({'canal': canal} if canal else {})}
        session.add(PalpiteLog(palpite=obj, alterado_por=actor, alterado_em=agora,
            acao=acao,
            valores_anteriores=serializar(anterior) if anterior else None,
            valores_novos=serializar({**valores_palpite(obj), **extras})))
        for atributo in ('_texto_original', '_canal'):
            if hasattr(obj, atributo):
                delattr(obj, atributo)


EXTRAS_DO_LOG = ('texto_original_whatsapp', 'canal')


@event.listens_for(PalpiteLog, "before_insert")
def completar_ids_do_log(mapper, connection, log):
    if log.acao == "criacao":
        anteriores = json.loads(log.valores_novos)
        log.valores_novos = serializar({**valores_palpite(log.palpite),
                                        **{k: anteriores[k] for k in EXTRAS_DO_LOG if anteriores.get(k)}})


@event.listens_for(Session, "do_orm_execute")
def impedir_gravacao_em_lote_sem_log(state):
    if state.is_update or state.is_delete:
        mapper = state.bind_mapper
        if mapper and mapper.class_ in (Palpite, PalpiteLog, Participante, Participacao, ParticipacaoLog):
            raise ValueError("Use gravação por objeto com auditoria; alterações em lote não são permitidas.")


CAMPOS_PARTICIPACAO = (
    "nome_exibicao", "papel", "status", "usuario_id", "participante_legado_id", "bolao_id",
    "entrou_em", "saiu_em", "pontua_desde", "entrada_legada", "rodada_entrada_id",
    "rodada_desistencia_id", "motivo_desistencia", "desistencia_registrada_em",
    "desistencia_registrada_por", "observacao", "email",
)


def valores_participacao(part):
    return {campo: getattr(part, campo) for campo in CAMPOS_PARTICIPACAO}


@event.listens_for(Session, "before_flush")
def auditar_participacoes(session, flush_context, instances):
    actor = current_user.id if has_request_context() and current_user.is_authenticated else None
    for part in list(session.new) + list(session.dirty):
        if not isinstance(part, Participacao):
            continue
        novo = part in session.new
        if not novo and not session.is_modified(part, include_collections=False):
            continue
        # Relações atribuídas podem ainda não ter sincronizado suas FKs antes do flush.
        bolao = part.bolao or session.get(Bolao, part.bolao_id)
        for campo in ("rodada_entrada", "rodada_desistencia"):
            estado = inspect(part).attrs
            if estado[campo].history.has_changes():
                rodada = getattr(part, campo)
            else:
                rodada_id = getattr(part, campo + "_id")
                rodada = session.get(Rodada, rodada_id) if rodada_id is not None else None
                if rodada_id is not None and rodada is None:
                    raise ValueError("Rodada inexistente.")
            if rodada and bolao and rodada.campeonato_id != bolao.campeonato_id:
                raise ValueError("A rodada da participação deve pertencer ao campeonato do bolão.")
        anterior = None
        if not novo:
            row = session.connection().execute(Participacao.__table__.select().where(
                Participacao.id == part.id)).mappings().one()
            anterior = {k: row[k] for k in CAMPOS_PARTICIPACAO}
        acao = "criacao" if novo else "edicao"
        if anterior:
            if part.status == "desistente" and anterior["status"] != "desistente":
                acao = "desistencia"
            elif part.status == "ativo" and anterior["status"] != "ativo":
                acao = "reativacao"
            elif part.status == "desistente":
                acao = "correcao"
            elif part.status != anterior["status"]:
                acao = "status"
        session.add(ParticipacaoLog(participacao=part, alterado_por=actor,
            alterado_em=agora_utc(), acao=acao,
            valores_anteriores=serializar(anterior) if anterior else None,
            valores_novos=serializar(valores_participacao(part))))


@event.listens_for(ParticipacaoLog, "before_insert")
def completar_log_participacao(mapper, connection, log):
    # Defaults, IDs e referências já resolvidos na persistência da participação.
    log.valores_novos = serializar(valores_participacao(log.participacao))
