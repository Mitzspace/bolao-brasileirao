import os
from datetime import datetime
from functools import wraps
from urllib.error import HTTPError, URLError

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from database import db
from models import BonusRodada, Campeonato, Jogo, Palpite, Participante, Resultado, Rodada
from services.importador_jogos import (
    buscar_jogos_football_data,
    buscar_resultados_football_data,
)
from services.sync import sync_informacoes_jogos
from utils import (
    validar_email,
    validar_nome,
    validar_senha,
    hash_senha,
    validar_arquivo_upload,
)

admin = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin.route("/")
@admin_required
def dashboard():
    campeonatos = Campeonato.query.count()
    rodadas = Rodada.query.count()
    jogos = Jogo.query.count()
    participantes = Participante.query.count()

    return render_template(
        "admin_dashboard.html",
        campeonatos=campeonatos,
        rodadas=rodadas,
        jogos=jogos,
        participantes=participantes,
    )


# ── Participantes ─────────────────────────────────────────────────────────────

@admin.route("/participantes")
@admin_required
def listar_participantes():
    todos = Participante.query.order_by(Participante.nome).all()
    return render_template("admin_participantes.html", participantes=todos)


@admin.route("/participante/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar_participante(id):
    p = Participante.query.get_or_404(id)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "").strip()
        eh_admin = "admin" in request.form

        # Validações
        if not validar_nome(nome):
            flash("Nome inválido. Deve ter pelo menos 2 caracteres.")
            return redirect(url_for("admin.editar_participante", id=p.id))

        if not validar_email(email):
            flash("Email inválido.")
            return redirect(url_for("admin.editar_participante", id=p.id))

        email_em_uso = (
            Participante.query
            .filter(Participante.email == email, Participante.id != p.id)
            .first()
        )
        if email_em_uso:
            flash("Já existe outro participante cadastrado com este e-mail.")
            return redirect(url_for("admin.editar_participante", id=p.id))

        if p.id == current_user.id and not eh_admin:
            flash("Você não pode remover sua própria permissão de administrador.")
            return redirect(url_for("admin.editar_participante", id=p.id))

        p.nome = nome
        p.email = email
        p.admin = eh_admin

        if senha:
            senha_valida, senha_msg = validar_senha(senha)
            if not senha_valida:
                flash(senha_msg)
                return redirect(url_for("admin.editar_participante", id=p.id))
            p.senha = hash_senha(senha)

        db.session.commit()
        flash(f'Participante "{p.nome}" atualizado com sucesso.')
        return redirect(url_for("admin.listar_participantes"))

    return render_template("admin_editar_participante.html", participante=p)


@admin.route("/participante/<int:id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(id):
    p = Participante.query.get_or_404(id)

    if p.id == current_user.id:
        flash("Voce nao pode alterar seu proprio perfil admin.")
        return redirect(url_for("admin.listar_participantes"))

    p.admin = not p.admin
    db.session.commit()

    acao = "promovido a admin" if p.admin else "rebaixado a participante"
    flash(f"{p.nome} foi {acao}.")
    return redirect(url_for("admin.listar_participantes"))


@admin.route("/participante/novo", methods=["POST"])
@admin_required
def cadastrar_participante():
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip().lower()
    senha = request.form.get("senha", "").strip() or "123456"
    eh_admin = "admin" in request.form

    # Validações
    if not validar_nome(nome):
        flash("Nome inválido. Deve ter pelo menos 2 caracteres.")
        return redirect(url_for("admin.listar_participantes"))

    if not validar_email(email):
        flash("Email inválido.")
        return redirect(url_for("admin.listar_participantes"))

    senha_valida, senha_msg = validar_senha(senha)
    if not senha_valida:
        flash(senha_msg)
        return redirect(url_for("admin.listar_participantes"))

    if Participante.query.filter_by(email=email).first():
        flash("Já existe um participante cadastrado com este e-mail.")
        return redirect(url_for("admin.listar_participantes"))

    p = Participante(
        nome=nome,
        email=email,
        senha=hash_senha(senha),
        admin=eh_admin
    )
    db.session.add(p)
    db.session.commit()
    flash(f'Participante "{nome}" cadastrado com sucesso!')
    return redirect(url_for("admin.listar_participantes"))


@admin.route("/participantes/mesclar", methods=["POST"])
@admin_required
def mesclar_participantes():
    origem_id = request.form.get("origem_id", type=int)
    destino_id = request.form.get("destino_id", type=int)

    if not origem_id or not destino_id:
        flash("Selecione os dois participantes para unificar.")
        return redirect(url_for("admin.listar_participantes"))

    if origem_id == destino_id:
        flash("Escolha participantes diferentes para unificar.")
        return redirect(url_for("admin.listar_participantes"))

    origem = Participante.query.get_or_404(origem_id)
    destino = Participante.query.get_or_404(destino_id)

    if origem.id == current_user.id:
        flash("Você não pode mesclar a sua própria conta como origem.")
        return redirect(url_for("admin.listar_participantes"))

    palpites_movidos = 0
    palpites_duplicados = 0

    for palpite in list(origem.palpites):
        existente = Palpite.query.filter_by(
            participante_id=destino.id,
            jogo_id=palpite.jogo_id,
        ).first()

        if existente:
            db.session.delete(palpite)
            palpites_duplicados += 1
        else:
            palpite.participante_id = destino.id
            palpites_movidos += 1

    bonus_movidos = 0
    bonus_duplicados = 0

    for bonus in list(origem.bonus_list):
        existente = BonusRodada.query.filter_by(
            participante_id=destino.id,
            rodada_id=bonus.rodada_id,
        ).first()

        if existente:
            db.session.delete(bonus)
            bonus_duplicados += 1
        else:
            bonus.participante_id = destino.id
            bonus_movidos += 1

    if origem.admin and not destino.admin:
        destino.admin = True

    nome_origem = origem.nome
    nome_destino = destino.nome
    db.session.delete(origem)
    db.session.commit()

    flash(
        f'"{nome_origem}" foi unificado em "{nome_destino}". '
        f"{palpites_movidos} palpites e {bonus_movidos} bônus movidos; "
        f"{palpites_duplicados} palpites e {bonus_duplicados} bônus duplicados descartados."
    )
    return redirect(url_for("admin.listar_participantes"))


@admin.route("/participante/<int:id>/excluir", methods=["POST"])
@admin_required
def excluir_participante(id):
    p = Participante.query.get_or_404(id)

    if p.id == current_user.id:
        flash("Você não pode excluir sua própria conta.")
        return redirect(url_for("admin.listar_participantes"))

    nome = p.nome
    for palpite in p.palpites:
        db.session.delete(palpite)

    db.session.delete(p)
    db.session.commit()

    flash(f'Participante "{nome}" foi excluído.')
    return redirect(url_for("admin.listar_participantes"))


# ── Campeonatos ───────────────────────────────────────────────────────────────

@admin.route("/campeonatos")
@admin_required
def listar_campeonatos():
    campeonatos = Campeonato.query.all()
    return render_template("admin_campeonatos.html", campeonatos=campeonatos)


@admin.route("/campeonato", methods=["GET", "POST"])
@admin_required
def cadastrar_campeonato():

    if request.method == "POST":
        nome = request.form["nome"].strip()
        ano = request.form["ano"]

        if not nome or not ano:
            flash("Nome e temporada são obrigatórios.")
            return redirect(url_for("admin.cadastrar_campeonato"))

        db.session.add(Campeonato(nome=nome, ano=ano))
        db.session.commit()

        flash(f'Campeonato "{nome}" cadastrado!')
        return redirect(url_for("admin.listar_campeonatos"))

    return render_template("admin_camp.html", campeonato=None)


@admin.route("/campeonato/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar_campeonato(id):
    camp = Campeonato.query.get_or_404(id)

    if request.method == "POST":
        nome = request.form["nome"].strip()
        ano = request.form["ano"]

        if not nome or not ano:
            flash("Nome e temporada são obrigatórios.")
            return redirect(url_for("admin.editar_campeonato", id=camp.id))

        camp.nome = nome
        camp.ano = ano
        db.session.commit()

        flash(f'Campeonato "{camp.nome}" atualizado!')
        return redirect(url_for("admin.listar_campeonatos"))

    return render_template("admin_camp.html", campeonato=camp)


@admin.route("/campeonato/<int:id>/excluir", methods=["POST"])
@admin_required
def excluir_campeonato(id):
    camp = Campeonato.query.get_or_404(id)
    nome = camp.nome

    # Exclusão em cascata: palpites -> resultados -> jogos -> rodadas -> campeonato
    for rodada in camp.rodadas:
        for jogo in rodada.jogos:
            if jogo.resultado:
                db.session.delete(jogo.resultado)
            for palpite in jogo.palpites:
                db.session.delete(palpite)
            db.session.delete(jogo)
        db.session.delete(rodada)

    db.session.delete(camp)
    db.session.commit()

    flash(f'Campeonato "{nome}" e todas as suas rodadas e jogos foram excluídos.')
    return redirect(url_for("admin.listar_campeonatos"))


# ── Rodadas ───────────────────────────────────────────────────────────────────

@admin.route("/rodada", methods=["GET", "POST"])
@admin_required
def cadastrar_rodada():

    campeonatos = Campeonato.query.all()

    if request.method == "POST":
        nome = request.form["nome"].strip()
        campeonato_id = request.form["campeonato_id"]
        aberta = "aberta" in request.form

        db.session.add(Rodada(nome=nome, campeonato_id=campeonato_id, aberta=aberta))
        db.session.commit()

        flash(f'Rodada "{nome}" cadastrada!')
        return redirect(url_for("admin.cadastrar_rodada"))

    return render_template("admin_rodada.html", campeonatos=campeonatos)


@admin.route("/rodada/<int:id>/toggle-aberta", methods=["POST"])
@admin_required
def toggle_rodada(id):
    rodada = Rodada.query.get_or_404(id)
    rodada.aberta = not rodada.aberta
    db.session.commit()

    estado = "aberta" if rodada.aberta else "fechada"
    flash(f'Rodada "{rodada.nome}" agora esta {estado}.')
    return redirect(url_for("admin.listar_campeonatos"))


@admin.route("/rodada/<int:id>/excluir", methods=["POST"])
@admin_required
def excluir_rodada(id):
    rodada = Rodada.query.get_or_404(id)
    nome = rodada.nome

    for jogo in rodada.jogos:
        if jogo.resultado:
            db.session.delete(jogo.resultado)
        for palpite in jogo.palpites:
            db.session.delete(palpite)
        db.session.delete(jogo)

    db.session.delete(rodada)
    db.session.commit()

    flash(f'Rodada "{nome}" e todos os seus jogos foram excluídos.')
    return redirect(url_for("admin.listar_campeonatos"))



# ── Jogos ─────────────────────────────────────────────────────────────────────

@admin.route("/jogo", methods=["GET", "POST"])
@admin_required
def cadastrar_jogo():

    rodadas = Rodada.query.all()

    if request.method == "POST":
        time_casa = request.form["time_casa"].strip()
        time_fora = request.form["time_fora"].strip()
        rodada_id = request.form["rodada_id"]
        data = request.form.get("data") or None
        especial = "especial" in request.form

        data_jogo = datetime.strptime(data, "%Y-%m-%dT%H:%M") if data else None

        db.session.add(Jogo(
            time_casa=time_casa,
            time_fora=time_fora,
            rodada_id=rodada_id,
            especial=especial,
            data=data_jogo,
        ))
        db.session.commit()

        flash(f"Jogo {time_casa} x {time_fora} cadastrado!")
        return redirect(url_for("admin.cadastrar_jogo"))

    return render_template("admin_jogo.html", rodadas=rodadas)


@admin.route("/jogo/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar_jogo(id):

    jogo = Jogo.query.get_or_404(id)
    rodadas = Rodada.query.all()

    if request.method == "POST":
        jogo.time_casa = request.form["time_casa"].strip()
        jogo.time_fora = request.form["time_fora"].strip()
        jogo.rodada_id = request.form["rodada_id"]
        jogo.especial = "especial" in request.form
        jogo.encerrado = "encerrado" in request.form

        data = request.form.get("data") or None
        jogo.data = datetime.strptime(data, "%Y-%m-%dT%H:%M") if data else None

        db.session.commit()

        flash(f"Jogo {jogo.time_casa} x {jogo.time_fora} atualizado!")
        return redirect(url_for("admin.cadastrar_resultados"))

    return render_template("admin_editar_jogo.html", jogo=jogo, rodadas=rodadas)


@admin.route("/jogo/<int:id>/encerrar", methods=["POST"])
@admin_required
def encerrar_jogo(id):
    jogo = Jogo.query.get_or_404(id)
    jogo.encerrado = True
    db.session.commit()
    flash(f"Jogo {jogo.time_casa} x {jogo.time_fora} encerrado para palpites.")
    return redirect(url_for("admin.cadastrar_resultados"))


@admin.route("/jogo/<int:id>/reabrir", methods=["POST"])
@admin_required
def reabrir_jogo(id):
    jogo = Jogo.query.get_or_404(id)
    jogo.encerrado = False
    db.session.commit()
    flash(f"Jogo {jogo.time_casa} x {jogo.time_fora} reaberto para palpites.")
    return redirect(url_for("admin.cadastrar_resultados"))


@admin.route("/jogo/<int:id>/excluir", methods=["POST"])
@admin_required
def excluir_jogo(id):
    jogo = Jogo.query.get_or_404(id)

    # Remove resultado e palpites vinculados antes de excluir o jogo
    if jogo.resultado:
        db.session.delete(jogo.resultado)

    for palpite in jogo.palpites:
        db.session.delete(palpite)

    db.session.delete(jogo)
    db.session.commit()

    flash(f"Jogo excluido.")
    return redirect(url_for("admin.cadastrar_resultados"))


# ── Resultados ────────────────────────────────────────────────────────────────

@admin.route("/resultados", methods=["GET", "POST"])
@admin_required
def cadastrar_resultados():

    jogos = Jogo.query.all()

    if request.method == "POST":
        jogo_id = request.form["jogo_id"]
        gols_casa_real = int(request.form["gols_casa_real"])
        gols_fora_real = int(request.form["gols_fora_real"])
        primeiro_gol_real = request.form.get("primeiro_gol_real") or None

        resultado = Resultado.query.filter_by(jogo_id=jogo_id).first()

        if resultado is None:
            resultado = Resultado(jogo_id=jogo_id)
            db.session.add(resultado)

        resultado.gols_casa_real = gols_casa_real
        resultado.gols_fora_real = gols_fora_real
        resultado.primeiro_gol_real = primeiro_gol_real

        db.session.commit()
        flash("Resultado salvo!")
        return redirect(url_for("admin.cadastrar_resultados"))

    return render_template("admin_resultados.html", jogos=jogos)


# ── Importar jogos ────────────────────────────────────────────────────────────

@admin.route("/importar-jogos", methods=["GET", "POST"])
@admin_required
def importar_jogos():

    campeonatos = Campeonato.query.all()

    if request.method == "POST":
        token = request.form.get("token") or os.environ.get("FOOTBALL_DATA_TOKEN")

        if not token:
            flash("Informe o token da API ou configure FOOTBALL_DATA_TOKEN.")
            return redirect(url_for("admin.importar_jogos"))

        campeonato_id = request.form["campeonato_id"]
        nome_rodada = request.form["nome_rodada"].strip()
        competicao = request.form["competicao"].strip().upper()
        temporada = request.form.get("temporada") or None
        rodada_api = request.form.get("rodada_api") or None
        data_inicio = request.form.get("data_inicio") or None
        data_fim = request.form.get("data_fim") or None

        try:
            jogos_importados = buscar_jogos_football_data(
                token=token, competicao=competicao, temporada=temporada,
                rodada=rodada_api, data_inicio=data_inicio, data_fim=data_fim,
            )
        except HTTPError as e:
            flash(f"Erro da API: {e.code}.")
            return redirect(url_for("admin.importar_jogos"))
        except URLError:
            flash("Nao foi possivel conectar na API.")
            return redirect(url_for("admin.importar_jogos"))

        rodada = Rodada.query.filter_by(
            campeonato_id=campeonato_id, nome=nome_rodada
        ).first()

        if rodada is None:
            rodada = Rodada(nome=nome_rodada, campeonato_id=campeonato_id, aberta=True)
            db.session.add(rodada)
            db.session.commit()

        criados = ignorados = 0

        for item in jogos_importados:
            if Jogo.query.filter_by(
                external_fonte="football-data.org",
                external_id=item["external_id"],
            ).first():
                ignorados += 1
                continue

            db.session.add(Jogo(
                time_casa=item["time_casa"], time_fora=item["time_fora"],
                data=item["data"], rodada_id=rodada.id, especial=False,
                external_fonte="football-data.org", external_id=item["external_id"],
            ))
            criados += 1

        db.session.commit()
        flash(f"Importacao concluida: {criados} jogos criados, {ignorados} ignorados.")
        return redirect(url_for("admin.importar_jogos"))

    return render_template("admin_importar_jogos.html", campeonatos=campeonatos)


# ── Importar resultados ───────────────────────────────────────────────────────

@admin.route("/importar-resultados", methods=["GET", "POST"])
@admin_required
def importar_resultados():

    if request.method == "POST":
        token = request.form.get("token") or os.environ.get("FOOTBALL_DATA_TOKEN")

        if not token:
            flash("Informe o token da API ou configure FOOTBALL_DATA_TOKEN.")
            return redirect(url_for("admin.importar_resultados"))

        competicao = request.form["competicao"].strip().upper()
        temporada = request.form.get("temporada") or None
        rodada_api = request.form.get("rodada_api") or None
        data_inicio = request.form.get("data_inicio") or None
        data_fim = request.form.get("data_fim") or None

        try:
            resultados_importados = buscar_resultados_football_data(
                token=token, competicao=competicao, temporada=temporada,
                rodada=rodada_api, data_inicio=data_inicio, data_fim=data_fim,
            )
        except HTTPError as e:
            flash(f"Erro da API: {e.code}.")
            return redirect(url_for("admin.importar_resultados"))
        except URLError:
            flash("Nao foi possivel conectar na API.")
            return redirect(url_for("admin.importar_resultados"))

        atualizados = ignorados = 0

        for item in resultados_importados:
            jogo = Jogo.query.filter_by(
                external_fonte="football-data.org",
                external_id=item["external_id"],
            ).first()

            if jogo is None:
                ignorados += 1
                continue

            resultado = Resultado.query.filter_by(jogo_id=jogo.id).first()
            if resultado is None:
                resultado = Resultado(jogo_id=jogo.id)
                db.session.add(resultado)

            resultado.gols_casa_real = item["gols_casa_real"]
            resultado.gols_fora_real = item["gols_fora_real"]
            atualizados += 1

        db.session.commit()
        flash(f"Importacao concluida: {atualizados} resultados atualizados, {ignorados} ignorados.")
        return redirect(url_for("admin.importar_resultados"))

    return render_template("admin_importar_resultados.html")


# ── Sync automático ───────────────────────────────────────────────────────────

@admin.route("/sync", methods=["GET", "POST"])
@admin_required
def sync():
    from urllib.error import HTTPError, URLError
    from services.sync import sync_jogos, sync_resultados

    campeonatos = Campeonato.query.all()

    if request.method == "POST":
        token = request.form.get("token") or os.environ.get("FOOTBALL_DATA_TOKEN")

        if not token:
            flash("Informe o token da API ou configure FOOTBALL_DATA_TOKEN no .env.")
            return redirect(url_for("admin.sync"))

        acao = request.form["acao"]
        competicao = request.form["competicao"].strip().upper()
        temporada = request.form.get("temporada") or None
        rodada_api = request.form.get("rodada_api") or None
        data_inicio = request.form.get("data_inicio") or None
        data_fim = request.form.get("data_fim") or None
        campeonato_completo = "campeonato_completo" in request.form

        try:
            if acao == "jogos":
                campeonato_id = request.form.get("campeonato_id")
                nome_rodada = request.form.get("nome_rodada", "").strip()

                if not campeonato_id:
                    flash("Selecione o campeonato no bolão.")
                    return redirect(url_for("admin.sync"))

                if not campeonato_completo and not nome_rodada and not rodada_api:
                    flash("Informe o nome da rodada ou o número da rodada na API.")
                    return redirect(url_for("admin.sync"))

                res = sync_jogos(
                    token=token,
                    campeonato_id=int(campeonato_id),
                    competicao=competicao,
                    nome_rodada=nome_rodada if not campeonato_completo else None,
                    temporada=temporada,
                    rodada_api=rodada_api if not campeonato_completo else None,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    campeonato_completo=campeonato_completo,
                )

                msg = (
                    f"Sincronização concluída! {res['criados']} jogos novos, "
                    f"{res['atualizados']} atualizados, "
                    f"{res['resultados_salvos']} resultados oficiais salvos "
                    f"em {res['rodadas_criadas']} rodadas criadas."
                )
                flash(msg)

            elif acao == "resultados":
                res = sync_resultados(
                    token=token,
                    competicao=competicao,
                    temporada=temporada,
                    rodada_api=rodada_api,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                )
                flash(f"Resultados sincronizados: {res['atualizados']} atualizados, {res['ignorados']} ignorados.")

            elif acao == "informacoes":
                campeonato_id = request.form.get("campeonato_id")

                if not campeonato_id:
                    flash("Selecione o campeonato no bolão.")
                    return redirect(url_for("admin.sync"))

                res = sync_informacoes_jogos(
                    token=token,
                    campeonato_id=int(campeonato_id),
                    competicao=competicao,
                    temporada=temporada,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                )
                msg = (
                    f"Informações sincronizadas! {res['atualizados']} jogos atualizados, "
                    f"{res['horarios_atualizados']} horários corrigidos, "
                    f"{res['resultados_salvos']} resultados salvos, "
                    f"{res['ignorados']} ignorados."
                )
                flash(msg)

        except HTTPError as e:
            flash(f"Erro da API ({e.code}): verifique o token e os parâmetros informados.")
        except URLError:
            flash("Não foi possível conectar à API. Verifique sua conexão com a internet.")

        return redirect(url_for("admin.sync"))

    return render_template("admin_sync.html", campeonatos=campeonatos)


# ── Lançar palpites dos participantes pelo Admin ──────────────────────────────

@admin.route("/palpites", methods=["GET", "POST"])
@admin_required
def gerenciar_palpites():
    from models import Palpite, Participante, Rodada, Jogo

    participantes = Participante.query.order_by(Participante.nome).all()
    campeonatos = Campeonato.query.all()

    # Filtros selecionados
    participante_id = request.args.get("participante_id", type=int)
    rodada_id = request.args.get("rodada_id", type=int)

    if request.method == "POST":
        p_id = request.form.get("participante_id", type=int)
        r_id = request.form.get("rodada_id", type=int)

        participante_sel = Participante.query.get_or_404(p_id)
        rodada_sel = Rodada.query.get_or_404(r_id)

        salvos = 0
        for jogo in rodada_sel.jogos:
            gols_casa = request.form.get(f"casa_{jogo.id}")
            gols_fora = request.form.get(f"fora_{jogo.id}")

            if gols_casa is None or gols_fora is None or gols_casa == "" or gols_fora == "":
                continue

            primeiro_gol = None
            if jogo.especial:
                primeiro_gol = request.form.get(f"primeiro_{jogo.id}") or None

            palpite = Palpite.query.filter_by(
                participante_id=participante_sel.id,
                jogo_id=jogo.id,
            ).first()

            if palpite is None:
                palpite = Palpite(
                    participante_id=participante_sel.id,
                    jogo_id=jogo.id,
                )
                db.session.add(palpite)

            palpite.gols_casa = int(gols_casa)
            palpite.gols_fora = int(gols_fora)
            palpite.primeiro_gol = primeiro_gol
            salvos += 1

        db.session.commit()
        flash(f"{salvos} palpites de '{participante_sel.nome}' para a '{rodada_sel.nome}' salvos com sucesso!")
        return redirect(url_for("admin.gerenciar_palpites", participante_id=p_id, rodada_id=r_id))

    rodada_sel = None
    participante_sel = None
    palpites_map = {}

    if rodada_id:
        rodada_sel = Rodada.query.get(rodada_id)

    if participante_id:
        participante_sel = Participante.query.get(participante_id)

    if rodada_sel and participante_sel:
        palpites = Palpite.query.filter_by(participante_id=participante_sel.id).all()
        palpites_map = {p.jogo_id: p for p in palpites}

    return render_template(
        "admin_palpites.html",
        participantes=participantes,
        campeonatos=campeonatos,
        rodada_sel=rodada_sel,
        participante_sel=participante_sel,
        palpites_map=palpites_map,
        rodada_id=rodada_id,
        participante_id=participante_id,
    )


# ── Importar planilha do bolão (.xlsx) ────────────────────────────────────────

@admin.route("/importar-planilha", methods=["GET", "POST"])
@admin_required
def importar_planilha():
    import glob
    from services.importador_planilha import importar_planilha_bolao

    campeonatos = Campeonato.query.all()

    # Procura planilhas existentes na pasta do usuário para facilitar
    pasta_downloads = os.environ.get("DOWNLOADS_FOLDER", r"c:\Users\Arquivos\Downloads\William")
    planilhas_locais = []
    if os.path.exists(pasta_downloads):
        planilhas_locais = glob.glob(os.path.join(pasta_downloads, "*.xlsx"))

    if request.method == "POST":
        campeonato_id = request.form.get("campeonato_id")
        novo_camp_nome = request.form.get("novo_campeonato_nome", "").strip()

        # Cria campeonato na hora se solicitado
        if novo_camp_nome:
            ano = request.form.get("novo_campeonato_ano") or datetime.now().year
            camp = Campeonato(nome=novo_camp_nome, ano=int(ano))
            db.session.add(camp)
            db.session.commit()
            campeonato_id = camp.id
        elif campeonato_id:
            campeonato_id = int(campeonato_id)
        else:
            flash("Selecione ou crie um campeonato de destino.")
            return redirect(url_for("admin.importar_planilha"))

        arquivo_upload = request.files.get("arquivo")
        planilha_selecionada = request.form.get("planilha_local")

        caminho_arquivo = None

        if arquivo_upload and arquivo_upload.filename:
            # Valida extensão do arquivo
            valido, msg = validar_arquivo_upload(arquivo_upload.filename, ["xlsx", "xls"])
            if not valido:
                flash(msg)
                return redirect(url_for("admin.importar_planilha"))

            # Salva temporariamente o arquivo enviado
            pasta_temp = os.path.join(os.getcwd(), "instance", "uploads")
            os.makedirs(pasta_temp, exist_ok=True)
            caminho_arquivo = os.path.join(pasta_temp, arquivo_upload.filename)
            arquivo_upload.save(caminho_arquivo)
        elif planilha_selecionada and os.path.exists(planilha_selecionada):
            caminho_arquivo = planilha_selecionada
        else:
            flash("Envie um arquivo .xlsx ou selecione uma planilha existente.")
            return redirect(url_for("admin.importar_planilha"))

        try:
            res = importar_planilha_bolao(caminho_arquivo, campeonato_id)
            flash(
                f"Planilha importada com sucesso! "
                f"{res['participantes_novos']} novos participantes, "
                f"{res['rodadas']} rodadas, "
                f"{res['jogos']} jogos e "
                f"{res['palpites']} palpites cadastrados."
            )
            return redirect(url_for("admin.listar_campeonatos"))
        except Exception as e:
            flash(f"Erro ao processar planilha: {str(e)}")
            return redirect(url_for("admin.importar_planilha"))

    return render_template(
        "admin_importar_planilha.html",
        campeonatos=campeonatos,
        planilhas_locais=planilhas_locais,
    )
