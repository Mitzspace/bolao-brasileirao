from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash

from database import db
from models import Participante
from services.acesso import pode_acessar_gestao
from extensions import limiter
from utils import validar_email, validar_senha, validar_nome, hash_senha

auth = Blueprint("auth", __name__)


@auth.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("Erro de segurança: sessão inválida. Tente novamente.")
    return redirect(url_for("auth.login"))


@auth.route("/cadastro", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def cadastro():

    if current_user.is_authenticated:
        return redirect(url_for("participante.escolher_bolao", continuar=1))

    if request.method == "POST":

        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        # Validações
        if not validar_nome(nome):
            flash("Nome inválido. Deve ter pelo menos 2 caracteres.")
            return redirect(url_for("auth.cadastro"))

        if not validar_email(email):
            flash("Email inválido.")
            return redirect(url_for("auth.cadastro"))

        senha_valida, senha_msg = validar_senha(senha)
        if not senha_valida:
            flash(senha_msg)
            return redirect(url_for("auth.cadastro"))

        if Participante.query.filter_by(email=email).first():
            flash("Este email ja esta cadastrado.")
            return redirect(url_for("auth.cadastro"))

        participante = Participante(
            nome=nome,
            email=email,
            senha=hash_senha(senha),
            admin=False,
        )

        db.session.add(participante)
        db.session.commit()

        login_user(participante)

        return redirect(url_for("participante.escolher_bolao", continuar=1))

    return render_template("cadastro.html")


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def login():

    if current_user.is_authenticated:
        return redirect(url_for("participante.escolher_bolao", continuar=1))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        # Validações
        if not validar_email(email):
            flash("Email inválido.")
            return redirect(url_for("auth.login"))

        if not senha:
            flash("Digite sua senha.")
            return redirect(url_for("auth.login"))

        p = Participante.query.filter_by(email=email).first()

        if not p or not p.conta_ativa or not p.senha or not check_password_hash(p.senha, senha):
            flash("Email ou senha invalidos.")
            return redirect(url_for("auth.login"))

        if not current_app.config["FEATURE_PARTICIPANTE_LOGIN"] and not pode_acessar_gestao(p):
            flash("Acesso disponível somente para responsáveis por bolões.")
            return redirect(url_for("auth.login"))

        login_user(p)

        return redirect(url_for("participante.escolher_bolao", continuar=1))

    return render_template("login.html")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop('bolao_id', None)
    session.pop('bolao_usuario_id', None)
    return redirect(url_for("auth.login"))


@auth.route("/resetar-senha", methods=["GET", "POST"])
def resetar_senha():
    """Orientação até haver recuperação com comprovação de posse da conta."""
    if request.method == "POST":
        # Mesmo comportamento para qualquer e-mail; nunca consulta ou altera contas.
        flash("Para recuperar o acesso, entre em contato com o administrador do sistema.")
        return redirect(url_for("auth.resetar_senha"))
    return render_template("resetar_senha.html")
