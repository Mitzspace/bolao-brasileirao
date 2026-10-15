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


def adicionar_responsavel(bolao, email, nome, senha, selecionada_id, quantidade_selecionada=1):
    """Concede acesso de responsável a uma conta neste bolão (mesmas regras da tela atual).
    Erros saem por abort() com a mensagem para o usuário. Faz commit."""
    from services.gestao_participantes import validar_dados_participante
    from utils import hash_senha, validar_email, validar_nome, validar_senha
    email = (email or '').strip().lower()
    if not validar_email(email):
        abort(400, description='Informe um e-mail válido.')
    usuario = Participante.query.filter_by(email=email).first()
    if usuario is None:
        nome = (nome or '').strip()
        valida, _ = validar_senha(senha or '')
        if not validar_nome(nome) or not valida:
            abort(400, description='Para uma nova conta, informe nome e senha válida (mínimo de 6 caracteres).')
        usuario = Participante(nome=nome, email=email, senha=hash_senha(senha),
                               admin=False, admin_global=False, conta_ativa=True)
        db.session.add(usuario)
        db.session.flush()
    if not usuario.conta_ativa or not usuario.senha:
        abort(400, description='A conta precisa estar ativa e ter senha para receber acesso.')
    vinculada = Participacao.query.filter_by(bolao_id=bolao.id, usuario_id=usuario.id).first()
    legada = Participacao.query.filter_by(bolao_id=bolao.id, participante_legado_id=usuario.id).first()
    if vinculada and legada and vinculada.id != legada.id:
        abort(409, description='Há dois registros para essa conta no bolão; revise o vínculo antes de conceder acesso.')
    part = vinculada or legada
    selecionada_id = (selecionada_id or '').strip()
    if selecionada_id:
        if not selecionada_id.isdecimal() or quantidade_selecionada != 1:
            abort(400)
        selecionada = Participacao.query.filter_by(id=int(selecionada_id), bolao_id=bolao.id).first_or_404()
        if part and part.id != selecionada.id:
            abort(409, description='Essa conta já está vinculada a outro participante.')
        part = selecionada
    if part and part.usuario_id not in (None, usuario.id):
        abort(409, description='O registro já está vinculado a outra conta.')
    if part and part.status == 'desistente':
        abort(409, description='Reative a participação pela tela de desistência antes de conceder acesso.')
    if part is None:
        erros = validar_dados_participante(bolao.id, usuario.nome, email)
        if erros:
            db.session.rollback()
            abort(409, description='Já existe participante com esse nome ou e-mail. Selecione o registro existente para vincular a conta.')
        part = Participacao(bolao=bolao, usuario=usuario, nome_exibicao=usuario.nome, email=email)
        db.session.add(part)
    part.usuario = usuario
    part.papel = 'responsavel'
    part.status = 'ativo'
    part.saiu_em = None
    db.session.commit()
    return part


def remover_responsavel(bolao, participacao_id):
    """Retira o acesso (a participação e o histórico ficam). Devolve True se foi o próprio acesso."""
    part = Participacao.query.filter_by(id=participacao_id, bolao_id=bolao.id,
        papel='responsavel', status='ativo').populate_existing().first_or_404()
    validar_retirada(part)
    propria = part.usuario_id == current_user.id
    part.papel = 'participante'
    db.session.commit()
    return propria
