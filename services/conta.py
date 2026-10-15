"""Perfil da conta do responsável: nome, e-mail de login e senha."""
from database import db
from models import Participante
from utils import hash_senha, validar_email, validar_nome, validar_senha, verificar_senha


def _confere_senha(usuario, senha_atual):
    if not senha_atual or not usuario.senha or not verificar_senha(senha_atual, usuario.senha):
        raise ValueError('Senha atual incorreta.')


def alterar_nome(usuario, nome):
    """Muda só o nome da conta; o nome exibido em cada bolão continua o mesmo."""
    nome = ' '.join((nome or '').split())
    if not validar_nome(nome) or len(nome) > 100:
        raise ValueError('Informe um nome entre 2 e 100 caracteres.')
    usuario.nome = nome
    db.session.commit()


def alterar_email(usuario, email, senha_atual):
    email = (email or '').strip().lower()
    if not validar_email(email) or len(email) > 100:
        raise ValueError('Informe um e-mail válido.')
    _confere_senha(usuario, senha_atual)
    if email == usuario.email:
        raise ValueError('Esse já é o seu e-mail de acesso.')
    if Participante.query.filter(Participante.email == email, Participante.id != usuario.id).first():
        raise ValueError('Já existe uma conta com esse e-mail.')
    usuario.email = email
    db.session.commit()


def alterar_senha(usuario, senha_atual, nova, confirmacao):
    _confere_senha(usuario, senha_atual)
    valida, mensagem = validar_senha(nova or '')
    if not valida:
        raise ValueError(mensagem)
    if nova != confirmacao:
        raise ValueError('A confirmação não confere com a nova senha.')
    if verificar_senha(nova, usuario.senha):
        raise ValueError('A nova senha precisa ser diferente da atual.')
    usuario.senha = hash_senha(nova)
    db.session.commit()
