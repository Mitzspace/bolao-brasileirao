from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash, generate_password_hash

from database import db
from models import Participante
from utils import validar_email, validar_senha, validar_nome, hash_senha

auth = Blueprint("auth", __name__)
limiter = Limiter(key_func=get_remote_address)


@auth.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("Erro de segurança: sessão inválida. Tente novamente.")
    return redirect(url_for("auth.login"))


@auth.route("/cadastro", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def cadastro():

    if current_user.is_authenticated:
        return redirect(url_for("participante.inicio"))

    if request.method == "POST":

        nome = request.form["nome"].strip()
        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

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

        return redirect(url_for("participante.inicio"))

    return render_template("cadastro.html")


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def login():

    if current_user.is_authenticated:
        return redirect(url_for("participante.inicio"))

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        senha = request.form["senha"]

        # Validações
        if not validar_email(email):
            flash("Email inválido.")
            return redirect(url_for("auth.login"))

        if not senha:
            flash("Digite sua senha.")
            return redirect(url_for("auth.login"))

        p = Participante.query.filter_by(email=email).first()

        if not p or not p.senha or not check_password_hash(p.senha, senha):
            flash("Email ou senha invalidos.")
            return redirect(url_for("auth.login"))

        login_user(p)

        return redirect(url_for("participante.inicio"))

    return render_template("login.html")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth.route("/resetar-senha", methods=["GET", "POST"])
def resetar_senha():
    """Rota para resetar senha (simplificada - em produção usar email)."""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not validar_email(email):
            flash("Email inválido.")
            return redirect(url_for("auth.resetar_senha"))

        participante = Participante.query.filter_by(email=email).first()

        if participante:
            # Em produção, aqui enviaria um email com link de reset
            # Por enquanto, apenas reset para senha padrão e avisa
            from utils import hash_senha
            nova_senha = "123456"
            participante.senha = hash_senha(nova_senha)
            db.session.commit()
            flash(f"Senha resetada para {nova_senha}. Por favor, faça login e altere sua senha.")
        else:
            flash("Se este email estiver cadastrado, você receberá instruções.")
            # Sempre mostra mesma mensagem por segurança (não revela se email existe)

        return redirect(url_for("auth.login"))

    return render_template("resetar_senha.html")
