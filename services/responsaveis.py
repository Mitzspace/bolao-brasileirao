"""Alterações de responsáveis serializadas por bolão, preservando participações."""
from flask import abort
from flask_login import current_user
from sqlalchemy import update
from database import db
from models import Bolao, Participacao, Participante


def bloquear_bolao(bolao_id):
    # UPDATE neutro obtém bloqueio de escrita no SQLite e de linha no PostgreSQL.
    # Todos os caminhos de retirada usam o mesmo bloqueio antes de contar responsáveis.
    db.session.execute(update(Bolao).where(Bolao.id == bolao_id).values(status=Bolao.status))
    autorizado = Participacao.query.filter_by(bolao_id=bolao_id, usuario_id=current_user.id,
        papel='responsavel', status='ativo').populate_existing().first()
    if autorizado is None:
        db.session.rollback()
        abort(403)


def validar_retirada(participacao):
    if participacao.papel != 'responsavel' or participacao.status != 'ativo':
        return
    outros = Participacao.query.join(Participante, Participante.id == Participacao.usuario_id).filter(
        Participacao.bolao_id == participacao.bolao_id, Participacao.id != participacao.id,
        Participacao.papel == 'responsavel', Participacao.status == 'ativo',
        Participante.conta_ativa.is_(True), Participante.senha.isnot(None)).count()
    if outros == 0:
        db.session.rollback()
        abort(409, description='Adicione outro responsável com conta ativa antes de remover o último.')
