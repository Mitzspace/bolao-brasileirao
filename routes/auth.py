"""Entrada e saída dos responsáveis. A tela de login é a da nova interface (/interface/)."""
from flask import Blueprint, flash, redirect, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash

from extensions import limiter
from models import Participante
from services.acesso import pode_acessar_gestao
from utils import validar_email

auth = Blueprint("auth", __name__)


def _voltar():
    return redirect(url_for("interface.index"))


@auth.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("Sessão de segurança expirada. Tente novamente.")
    return _voltar()


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def login():
    if request.method == "GET" or current_user.is_authenticated:
        return _voltar()

    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "")
    if not validar_email(email):
        flash("Email inválido.")
        return _voltar()
    if not senha:
        flash("Digite sua senha.")
        return _voltar()

    p = Participante.query.filter_by(email=email).first()
    if not p or not p.conta_ativa or not p.senha or not check_password_hash(p.senha, senha):
        flash("Email ou senha invalidos.")
        return _voltar()
    if not pode_acessar_gestao(p):
        flash("Acesso disponível somente para responsáveis por bolões.")
        return _voltar()

    # "Manter conectado": o login continua após fechar o navegador (30 dias, config.REMEMBER_COOKIE_*).
    login_user(p, remember=request.form.get("lembrar") == "1")
    return _voltar()


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop('bolao_id', None)
    session.pop('bolao_usuario_id', None)
    return _voltar()
