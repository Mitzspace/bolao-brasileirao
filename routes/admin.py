from services.pontuacao import calcular_pontuacao
import os
from datetime import datetime
from services.relogio import agora_brasilia
from functools import wraps
from pathlib import Path
from urllib.error import HTTPError, URLError

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from database import db
from models import Bolao, BonusRodada, Campeonato, Jogo, Palpite, Participante, Participacao, Resultado, Rodada, agora_utc
from services.contexto_bolao import bolao_atual, campeonatos_do_contexto, responsavel_atual, validar_rodada
from services.sync import sync_informacoes_jogos
from services.importador_jogos import buscar_jogos_football_data, buscar_resultados_football_data
from services.validacao_formularios import texto, inteiro, data_jogo as validar_data_jogo, placar
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
        if not current_user.admin and not responsavel_atual():
            abort(403)
        if Bolao.query.first() and not bolao_atual():
            abort(403)
        if bolao_atual() and not responsavel_atual():
            abort(403)
        if not current_app.config['FEATURE_PARTICIPANTE_LOGIN']:
            from services.permissoes import validar_escopo_admin
            validar_escopo_admin(f.__name__, kwargs)
            return f(*args, **kwargs)
        # Compatibilidade do fluxo legado reativável.
        if (bolao_atual() and Bolao.query.count() > 1 and not current_user.admin_global
                and f.__name__ not in ('dashboard', 'gerenciar_palpites')):
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin.route('/responsaveis', methods=['GET', 'POST'])
@admin_required
def responsaveis():
    from services.responsaveis import bloquear_bolao, validar_retirada
    bolao = bolao_atual()
    if request.method == 'POST':
        bloquear_bolao(bolao.id)
        acao = request.form.get('acao')
        if acao == 'adicionar':
            email = request.form.get('email', '').strip().lower()
            if not validar_email(email):
                abort(400, description='Informe um e-mail válido.')
            usuario = Participante.query.filter_by(email=email).first()
            if usuario is None:
                nome = request.form.get('nome', '').strip()
                senha = request.form.get('senha', '')
                valida, mensagem = validar_senha(senha)
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
            selecionada_id = request.form.get('participacao_id', '').strip()
            if selecionada_id:
                if not selecionada_id.isdecimal() or len(request.form.getlist('participacao_id')) != 1:
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
                from services.gestao_participantes import validar_dados_participante
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
            flash('Responsável adicionado a este bolão. Os demais bolões não foram alterados.')
        elif acao == 'remover':
            part = Participacao.query.filter_by(id=request.form.get('participacao_id', type=int),
                bolao_id=bolao.id, papel='responsavel', status='ativo').populate_existing().first_or_404()
            validar_retirada(part)
            propria = part.usuario_id == current_user.id
            part.papel = 'participante'
            db.session.commit()
            flash('Acesso de responsável removido; participação e histórico preservados.')
            if propria:
                return redirect(url_for('auth.logout'))
        else:
            abort(400)
        return redirect(url_for('admin.responsaveis'))
    pessoas = Participacao.query.filter_by(bolao_id=bolao.id, papel='responsavel', status='ativo').all()
    participantes_sem_conta = Participacao.query.filter_by(bolao_id=bolao.id, usuario_id=None, status='ativo').order_by(Participacao.nome_exibicao).all()
    return render_template('responsaveis.html', responsaveis=pessoas, participantes_sem_conta=participantes_sem_conta)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin.route("/")
@admin_required
def dashboard():
    bolao = bolao_atual()
    campeonatos = 1 if bolao else Campeonato.query.count()
    rodadas = Rodada.query.filter_by(campeonato_id=bolao.campeonato_id).count() if bolao else Rodada.query.count()
    jogos = Jogo.query.join(Rodada).filter(Rodada.campeonato_id==bolao.campeonato_id).count() if bolao else Jogo.query.count()
    participantes = Participacao.query.filter_by(bolao_id=bolao.id).count() if bolao else Participante.query.count()

    return render_template(
        "admin_dashboard.html",
        campeonatos=campeonatos,
        rodadas=rodadas,
        jogos=jogos,
        participantes=participantes,
    )


# ── Participantes ─────────────────────────────────────────────────────────────

@admin.route('/participacoes/nova', methods=['POST'])
@admin_required
def criar_participacao():
    from services.responsaveis import bloquear_bolao
    from services.gestao_participantes import validar_dados_participante, tela_participantes
    bolao = bolao_atual()
    bloquear_bolao(bolao.id)
    nome = request.form.get('nome_exibicao', '').strip()
    observacao = request.form.get('observacao', '').strip() or None
    email = request.form.get('email', '').strip().lower() or None
    erros = validar_dados_participante(bolao.id, nome, email)
    rodada_id = request.form.get('rodada_entrada_id', type=int)
    rodada = Rodada.query.filter_by(id=rodada_id, campeonato_id=bolao.campeonato_id).first() if rodada_id else None
    if rodada is None or len(request.form.getlist('rodada_entrada_id')) != 1:
        erros['rodada_entrada_id'] = 'Selecione uma rodada de entrada deste campeonato.'
    if erros:
        db.session.rollback()
        return tela_participantes(erros=erros, dados=request.form, status_http=422)
    db.session.add(Participacao(bolao_id=bolao.id, nome_exibicao=nome,
                               papel='participante', status='ativo', observacao=observacao, email=email,
                               rodada_entrada_id=rodada.id))
    db.session.commit()
    flash('Participante cadastrado sem conta de acesso.')
    return redirect(url_for('admin.listar_participantes'))


@admin.route('/participacoes/<int:id>/editar', methods=['POST'])
@admin_required
def editar_participacao(id):
    from services.responsaveis import bloquear_bolao
    from services.gestao_participantes import validar_dados_participante, tela_participantes
    bloquear_bolao(bolao_atual().id)
    pessoa = Participacao.query.filter_by(id=id, bolao_id=bolao_atual().id).first_or_404()
    nome = request.form.get('nome_exibicao', '').strip()
    email = request.form.get('email', pessoa.email or '').strip().lower() or None
    erros = validar_dados_participante(bolao_atual().id, nome, email, id)
    responsavel = request.form.get('responsavel')
    if responsavel is not None and responsavel not in {'sim', 'nao'}:
        erros['responsavel'] = 'Selecione Sim ou Não.'
    if responsavel == 'sim' and pessoa.status != 'ativo':
        erros['responsavel'] = 'Reative o participante antes de torná-lo responsável.'
    if erros:
        db.session.rollback()
        return tela_participantes(erros=erros, dados=request.form, edicao_id=id, status_http=422)
    if responsavel == 'nao':
        from services.responsaveis import validar_retirada
        validar_retirada(pessoa)
        pessoa.papel = 'participante'
    elif responsavel == 'sim':
        pessoa.papel = 'responsavel'
    pessoa.email = email
    pessoa.nome_exibicao = nome
    if 'observacao' in request.form:
        pessoa.observacao = request.form.get('observacao', '').strip() or None
    db.session.commit()
    flash('Participante atualizado somente neste bolão.')
    return redirect(url_for('admin.listar_participantes'))


@admin.route('/participacoes/<int:id>/status', methods=['POST'])
@admin_required
def alterar_status_participacao(id):
    from services.responsaveis import bloquear_bolao, validar_retirada
    bloquear_bolao(bolao_atual().id)
    pessoa = Participacao.query.filter_by(id=id, bolao_id=bolao_atual().id).populate_existing().first_or_404()
    if pessoa.status == 'desistente':
        abort(409, description='Use a tela de desistência para corrigir ou reativar com revisão dos palpites.')
    acao = request.form.get('acao')
    if acao == 'remover':
        validar_retirada(pessoa)
        if pessoa.status == 'ativo':
            pessoa.status = 'removido'
            pessoa.saiu_em = agora_utc()
    elif acao == 'reativar':
        # Reativação do registro não concede acesso administrativo implicitamente.
        # O papel de responsável volta apenas pela tela de Configurações.
        if pessoa.status != 'ativo':
            pessoa.papel = 'participante'
            pessoa.status = 'ativo'
            pessoa.saiu_em = None
    else:
        abort(400)
    propria_remocao = pessoa.usuario_id == current_user.id and pessoa.status != 'ativo'
    db.session.commit()
    flash('Status atualizado; palpites, pontos e histórico foram preservados.')
    if propria_remocao:
        return redirect(url_for('auth.logout'))
    return redirect(url_for('admin.listar_participantes'))


@admin.route('/participacoes/<int:id>/desistencia', methods=['GET', 'POST'])
@admin_required
def gerenciar_desistencia(id):
    import hmac
    from itsdangerous import URLSafeTimedSerializer, BadSignature
    from services.contexto_bolao import opcoes_rodadas, ordem_rodada
    from services.desistencias import preparar, aplicar, historico_visivel
    from services.elegibilidade import REGRA_DESISTENCIA
    from services.responsaveis import bloquear_bolao
    from services.resumo_boloes import rodadas_de_referencia
    bolao = bolao_atual()
    if request.method == 'POST':
        bloquear_bolao(bolao.id)
    pessoa = Participacao.query.filter_by(id=id, bolao_id=bolao.id).populate_existing().first_or_404()
    acao = request.values.get('acao', 'corrigir' if pessoa.status == 'desistente' else 'registrar')
    opcoes = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    referencia = rodadas_de_referencia({bolao.campeonato_id})[bolao.campeonato_id]['rodada']
    padrao = pessoa.rodada_desistencia or referencia or (opcoes[0] if opcoes else None)
    rodada_id = request.form.get('rodada_desistencia_id', type=int) if request.method == 'POST' else (padrao.id if padrao else None)
    rodada = next((r for r in opcoes if r.id == rodada_id), None)
    motivo = request.form.get('motivo_desistencia', '').strip() if request.method == 'POST' else (pessoa.motivo_desistencia or '')
    plano = None
    erro = None
    codigo = 200
    token = None
    if request.method == 'POST':
        if acao in {'registrar', 'corrigir'} and (rodada is None or len(request.form.getlist('rodada_desistencia_id')) != 1):
            erro, codigo = 'Selecione uma rodada de desistência deste campeonato.', 422
        elif acao in {'registrar', 'corrigir'} and pessoa.rodada_entrada and (
                ordem_rodada(rodada) < ordem_rodada(pessoa.rodada_entrada)):
            erro, codigo = 'A desistência não pode ser anterior à rodada de entrada.', 422
        else:
            plano = preparar(pessoa, acao, rodada, motivo)
            assinador = URLSafeTimedSerializer(current_app.secret_key, salt='confirmacao-desistencia-v1')
            if request.form.get('confirmar') == 'sim':
                try:
                    payload = assinador.loads(request.form.get('confirmacao', ''), max_age=1800)
                    valido = (payload.get('autor') == current_user.id and
                              hmac.compare_digest(payload.get('estado', ''), plano.fingerprint))
                except (BadSignature, TypeError, AttributeError):
                    valido = False
                restaurar = request.form.get('restaurar_palpites')
                if not valido:
                    erro, codigo = 'A prévia expirou ou os dados mudaram. Confira a lista atualizada e confirme novamente.', 409
                elif plano.restauraveis and restaurar not in {'sim', 'nao'}:
                    erro, codigo = 'Escolha se os palpites guardados devem voltar a valer.', 422
                else:
                    aplicar(pessoa, plano, current_user.id, restaurar == 'sim')
                    flash('Participação atualizada. Histórico preservado e pontuação recalculada pelas regras e resultados oficiais.')
                    if pessoa.usuario_id == current_user.id and pessoa.status != 'ativo':
                        return redirect(url_for('auth.logout'))
                    return redirect(url_for('admin.gerenciar_desistencia', id=id,
                                            acao='corrigir' if pessoa.status == 'desistente' else 'restaurar'))
            token = assinador.dumps({'autor': current_user.id, 'estado': plano.fingerprint})
        db.session.rollback()  # A prévia nunca grava dados, nem mantém bloqueio.
    from models import ParticipacaoLog
    logs = ParticipacaoLog.query.filter_by(participacao_id=id).order_by(ParticipacaoLog.id.desc()).all()
    guardados = (Palpite.query.filter_by(participacao_id=id, excluido_por_desistencia=True)
                 .join(Jogo).order_by(Jogo.rodada_id, Jogo.id).all())
    return render_template('desistencia.html', pessoa=pessoa, acao=acao, rodadas=opcoes,
        rodada_id=rodada_id, motivo=motivo, plano=plano, confirmacao=token,
        erro=erro, regra=REGRA_DESISTENCIA, logs=historico_visivel(logs, opcoes), guardados=guardados), codigo

@admin.route("/participantes")
@admin_required
def listar_participantes():
    if not current_app.config['FEATURE_PARTICIPANTE_LOGIN']:
        from services.gestao_participantes import tela_participantes
        return tela_participantes()
    query = Participante.query
    if bolao_atual():
        query = query.join(Participacao, Participacao.participante_legado_id==Participante.id).filter(Participacao.bolao_id==bolao_atual().id)
    todos = query.order_by(Participante.nome).all()
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
    flash("A mesclagem automática foi desativada para preservar participações e logs. Solicite a revisão do administrador global.")
    return redirect(url_for("admin.listar_participantes"))


@admin.route("/participante/<int:id>/excluir", methods=["POST"])
@admin_required
def excluir_participante(id):
    p = Participante.query.get_or_404(id)

    if p.id == current_user.id:
        flash("Você não pode excluir sua própria conta.")
        return redirect(url_for("admin.listar_participantes"))

    if p.admin_global:
        abort(403)
    nome = p.nome
    if not current_app.config['FEATURE_PARTICIPANTE_LOGIN']:
        from services.responsaveis import bloquear_bolao, validar_retirada
        bloquear_bolao(bolao_atual().id)
    query = Participacao.query.filter_by(participante_legado_id=p.id)
    if bolao_atual():
        query = query.filter_by(bolao_id=bolao_atual().id)
    participacoes = query.all()
    if bolao_atual() and not participacoes:
        abort(404)
    for participacao in participacoes:
        if not current_app.config['FEATURE_PARTICIPANTE_LOGIN']:
            validar_retirada(participacao)
        participacao.status = "removido"
        participacao.saiu_em = agora_utc()
    db.session.commit()

    flash(f'Participante "{nome}" removido do bolão; palpites, pontos e histórico foram preservados.')
    return redirect(url_for("admin.listar_participantes"))


# ── Campeonatos ───────────────────────────────────────────────────────────────

@admin.route("/campeonatos")
@admin_required
def listar_campeonatos():
    campeonatos = campeonatos_do_contexto()
    return render_template("admin_campeonatos.html", campeonatos=campeonatos)


@admin.route("/campeonato", methods=["GET", "POST"])
@admin_required
def cadastrar_campeonato():

    if request.method == "POST":
        abort(400, description="Crie o campeonato junto com seu bolão em Criar bolão.")
    return redirect(url_for("participante.criar_bolao"))


@admin.route("/campeonato/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar_campeonato(id):
    camp = Campeonato.query.get_or_404(id)

    if request.method == "POST":
        try:
            nome = texto(request.form.get('nome'), 'Nome')
            ano = inteiro(request.form.get('ano'), 'Temporada', 1, 9999)
        except ValueError as e:
            flash(str(e))
            return render_template('admin_camp.html', campeonato=camp), 400

        camp.nome = nome
        camp.ano = ano
        if "codigo_api" in request.form:
            camp.codigo_api = (request.form.get("codigo_api") or "BSA").strip().upper()
        db.session.commit()

        flash(f'Campeonato "{camp.nome}" atualizado!')
        return redirect(url_for("admin.listar_campeonatos"))

    return render_template("admin_camp.html", campeonato=camp)


@admin.route("/campeonato/<int:id>/excluir", methods=["POST"])
@admin_required
def excluir_campeonato(id):
    camp = Campeonato.query.get_or_404(id)
    if camp.boloes or any(rodada.bonus_list or any(jogo.palpites for jogo in rodada.jogos) for rodada in camp.rodadas):
        flash("Este campeonato possui bolão ou histórico e não pode ser excluído.")
        return redirect(url_for("admin.listar_campeonatos"))
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

    campeonatos = campeonatos_do_contexto()

    if request.method == "POST":
        try:
            nome = texto(request.form.get('nome'), 'Nome')
            campeonato_id = inteiro(request.form.get('campeonato_id'), 'Campeonato', 1)
        except ValueError as e:
            flash(str(e))
            return render_template('admin_rodada.html', campeonatos=campeonatos), 400
        if not any(c.id == campeonato_id for c in campeonatos):
            abort(404)
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
    if rodada.bonus_list or any(jogo.palpites for jogo in rodada.jogos):
        flash("Esta rodada possui palpites ou créditos históricos e não pode ser excluída.")
        return redirect(url_for("admin.listar_campeonatos"))
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

    rodadas = Rodada.query.filter_by(campeonato_id=bolao_atual().campeonato_id).all() if bolao_atual() else Rodada.query.all()

    if request.method == "POST":
        try:
            time_casa = texto(request.form.get('time_casa'), 'Time da casa')
            time_fora = texto(request.form.get('time_fora'), 'Time de fora')
            rodada_id = inteiro(request.form.get('rodada_id'), 'Rodada', 1)
            data_jogo = validar_data_jogo(request.form.get('data'))
        except ValueError as e:
            flash(str(e))
            return render_template('admin_jogo.html', rodadas=rodadas), 400
        validar_rodada(Rodada.query.get_or_404(rodada_id))
        especial = "especial" in request.form

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
    rodadas = Rodada.query.filter_by(campeonato_id=bolao_atual().campeonato_id).all() if bolao_atual() else Rodada.query.all()

    if request.method == "POST":
        try:
            time_casa = texto(request.form.get('time_casa'), 'Time da casa')
            time_fora = texto(request.form.get('time_fora'), 'Time de fora')
            rodada_id = inteiro(request.form.get('rodada_id'), 'Rodada', 1)
            data = validar_data_jogo(request.form.get('data'))
        except ValueError as e:
            flash(str(e))
            return render_template('admin_editar_jogo.html', jogo=jogo, rodadas=rodadas), 400
        validar_rodada(Rodada.query.get_or_404(rodada_id))
        jogo.time_casa = time_casa
        jogo.time_fora = time_fora
        jogo.rodada_id = rodada_id
        jogo.especial = "especial" in request.form
        jogo.encerrado = "encerrado" in request.form

        jogo.data = data

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
    if jogo.palpites:
        flash("Este jogo possui palpites e histórico e não pode ser excluído.")
        return redirect(url_for("admin.cadastrar_resultados"))

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

    consulta = Jogo.query.join(Rodada)
    if bolao_atual():
        consulta = consulta.filter(Rodada.campeonato_id == bolao_atual().campeonato_id)
    rodada_id = request.args.get('rodada_id', type=int)
    if rodada_id:
        validar_rodada(Rodada.query.get_or_404(rodada_id))
        consulta = consulta.filter(Jogo.rodada_id == rodada_id)
    jogos = consulta.all()

    if request.method == "POST":
        try:
            jogo_id = inteiro(request.form.get('jogo_id'), 'Jogo', 1)
            gols_casa_real, gols_fora_real = placar(
                request.form.get('gols_casa_real'), request.form.get('gols_fora_real'))
        except ValueError as e:
            flash(str(e))
            return render_template('admin_resultados.html', jogos=jogos), 400
        validar_rodada(Jogo.query.get_or_404(jogo_id).rodada)
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

    campeonatos = campeonatos_do_contexto()

    if request.method == "POST":
        token = request.form.get("token") or os.environ.get("FOOTBALL_DATA_TOKEN")

        if not token:
            flash("Informe o token da API ou configure FOOTBALL_DATA_TOKEN.")
            return redirect(url_for("admin.importar_jogos"))

        try:
            campeonato_id = inteiro(request.form.get('campeonato_id'), 'Campeonato', 1)
            nome_rodada = texto(request.form.get('nome_rodada'), 'Rodada')
            competicao = texto(request.form.get('competicao'), 'Competição', 20).upper()
        except ValueError as e:
            flash(str(e))
            return render_template('admin_importar_jogos.html', campeonatos=campeonatos), 400
        if not any(c.id == campeonato_id for c in campeonatos):
            abort(404)
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

        criados = ignorados = atualizados  = 0

        for item in jogos_importados:
            jogo = Jogo.query.filter_by(
                external_fonte="football-data.org",
                external_id=item["external_id"],
            ).first()

            if jogo:
                # Jogo já existe: só preenche/atualiza a data.
                if item["data"] and jogo.data != item["data"]:
                    jogo.data = item["data"]
                    atualizados += 1
                else:
                    ignorados += 1
                continue

            db.session.add(Jogo(
                time_casa=item["time_casa"], time_fora=item["time_fora"],
                data=item["data"], rodada_id=rodada.id, especial=False,
                external_fonte="football-data.org", external_id=item["external_id"],
            ))
            criados += 1

        db.session.commit()
        flash(
            f"Importacao concluida: {criados} jogos criados, "
            f"{atualizados} datas atualizadas,{ignorados} ignorados."
            )
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

        try:
            competicao = texto(request.form.get('competicao'), 'Competição', 20).upper()
        except ValueError as e:
            flash(str(e))
            return render_template('admin_importar_resultados.html'), 400
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
    from services.sync import sync_jogos, sync_resultados, sync_informacoes_jogos

    campeonatos = campeonatos_do_contexto()

    if request.method == "POST":
        token = request.form.get("token") or os.environ.get("FOOTBALL_DATA_TOKEN")

        if not token:
            flash("Informe o token da API ou configure FOOTBALL_DATA_TOKEN no .env.")
            return redirect(url_for("admin.sync"))

        acao = request.form.get('acao')
        try:
            competicao = texto(request.form.get('competicao'), 'Competição', 20).upper()
            if acao not in {'jogos', 'resultados', 'informacoes'}:
                raise ValueError('Selecione uma ação de sincronização válida.')
            if acao in {'jogos', 'informacoes'}:
                campeonato = inteiro(request.form.get('campeonato_id'), 'Campeonato', 1)
                if not any(c.id == campeonato for c in campeonatos):
                    abort(404)
        except ValueError as e:
            flash(str(e))
            return render_template('admin_sync.html', campeonatos=campeonatos), 400
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
                if res.get("nao_casados"):
                    msg += " Sem correspondência: " + "; ".join(res["nao_casados"][:5])
                flash(msg)

        except HTTPError as e:
            flash(f"Erro da API ({e.code}): verifique o token e os parâmetros informados.")
        except URLError:
            flash("Não foi possível conectar à API. Verifique sua conexão com a internet.")

        return redirect(url_for("admin.sync"))

    return render_template("admin_sync.html", campeonatos=campeonatos)


@admin.route('/palpites/previa-whatsapp', methods=['POST'])
@admin_required
def previa_whatsapp():
    from flask import jsonify
    from services.parser_whatsapp import ler_mensagem, rodadas_informadas
    from services.texto_lancamento import assinatura
    from services.elegibilidade import participa_na_rodada
    bolao = bolao_atual()
    if not bolao:
        abort(400, description='Selecione um bolão.')
    pessoa = Participacao.query.filter_by(id=request.form.get('participante_id', type=int), bolao_id=bolao.id).first_or_404()
    rodada = Rodada.query.get_or_404(request.form.get('rodada_id', type=int))
    validar_rodada(rodada)
    if not participa_na_rodada(pessoa, rodada):
        abort(409, description='Esta pessoa não participa desta rodada.')
    texto = request.form.get('texto', '')
    if not texto.strip() or len(texto) > 20000 or len(texto.splitlines()) > 200:
        return jsonify(erro='Cole uma mensagem com até 20.000 caracteres e 200 linhas.'), 422
    import re
    cabecalhos = rodadas_informadas(texto)
    numeros = re.findall(r'\d+', rodada.nome)
    if cabecalhos and (len(numeros) != 1 or cabecalhos != {int(numeros[0])}):
        return jsonify(erro=f'O cabeçalho informa rodada(s) {", ".join(map(str, sorted(cabecalhos)))}; a seleção é {rodada.nome}. Ajuste a rodada ou a mensagem antes de continuar.'), 422
    jogos = list(rodada.jogos)
    existentes = {p.jogo_id:p for p in Palpite.query.filter_by(participacao_id=pessoa.id).join(Jogo).filter(Jogo.rodada_id == rodada.id)}
    linhas = ler_mensagem(texto, jogos)
    opcoes = []
    for jogo in jogos:
        avisos = []
        if jogo.id in existentes:
            avisos.append('Palpite existente: será sobrescrito ao salvar, com histórico.')
        bloqueado = jogo.id in existentes and existentes[jogo.id].excluido_por_desistencia
        if bloqueado:
            avisos.append('Após desistência: restaure no histórico antes de lançar.')
        if not rodada.aberta or jogo.encerrado or (jogo.data and jogo.data <= agora_brasilia()):
            avisos.append('Jogo iniciado ou fechado: lançamento permitido ao responsável e auditado.')
        opcoes.append({'id':jogo.id, 'nome':f'{jogo.time_casa} × {jogo.time_fora}', 'avisos':avisos, 'bloqueado':bloqueado, 'primeiro_gol_permitido':bool(jogo.especial)})
    return jsonify(linhas=linhas, jogos=opcoes,
        reconhecido=any(i['jogo_id'] is not None for i in linhas),
        token=assinatura(texto, current_user.id, bolao.id, pessoa.id, rodada.id))


# ── Lançar palpites dos participantes pelo Admin ──────────────────────────────

@admin.route("/palpites", methods=["GET", "POST"])
@admin_required
def gerenciar_palpites():
    from models import Palpite, Participante, Rodada, Jogo
    from services.elegibilidade import participa_na_rodada
    from services.contexto_bolao import ordem_rodada
    from services.fluxo_lancamento import lembrar_rodada, rodada_padrao, vizinhos, proximo_pendente
    from services.resumo_boloes import participantes_pendentes

    bolao = bolao_atual()
    participantes = (Participacao.query.filter(Participacao.bolao_id == bolao.id,
                        Participacao.status.in_(['ativo', 'desistente'])).order_by(Participacao.nome_exibicao, Participacao.id).all()
                     if bolao else Participante.query.order_by(Participante.nome).all())
    campeonatos = campeonatos_do_contexto()

    def pessoa_selecionada(id, rodada=None):
        if bolao:
            pessoa = Participacao.query.filter(Participacao.id == id, Participacao.bolao_id == bolao.id,
                Participacao.status.in_(['ativo', 'desistente'])).populate_existing().first_or_404()
            if rodada and not participa_na_rodada(pessoa, rodada):
                abort(409, description='Esta pessoa não participa desta rodada. Confira entrada e desistência.')
            return pessoa
        return Participante.query.get_or_404(id)

    # Filtros selecionados
    participante_id = request.args.get("participante_id", type=int)
    rodada_id = request.args.get("rodada_id", type=int)
    rodadas = sorted([r for c in campeonatos for r in c.rodadas], key=ordem_rodada)
    if request.method == 'GET' and bolao and not request.args.get('rodada_id'):
        padrao = rodada_padrao(bolao, rodadas)
        rodada_id = padrao.id if padrao else None

    erros = {}
    valores = None
    if request.method == "POST":
        if bolao:
            from services.responsaveis import bloquear_bolao
            bloquear_bolao(bolao.id)
        if any(len(request.form.getlist(c)) != 1 for c in ('participante_id', 'rodada_id')):
            abort(400, description='Selecione uma pessoa e uma rodada.')
        acao = request.form.get('acao', 'ficar')
        if acao not in {'ficar', 'proximo'} or len(request.form.getlist('acao')) > 1:
            abort(400, description='Ação de salvamento inválida.')
        participante_id = request.form.get('participante_id', type=int)
        rodada_id = request.form.get('rodada_id', type=int)
        rodada_sel = Rodada.query.get_or_404(rodada_id)
        validar_rodada(rodada_sel)
        participante_sel = pessoa_selecionada(participante_id, rodada_sel)
        existentes = {p.jogo_id: p for p in Palpite.query.filter_by(
            **({'participacao_id': participante_sel.id} if bolao else {'participante_id': participante_sel.id})
        ).join(Jogo).filter(Jogo.rodada_id == rodada_id).all()}
        from services.lancamento_lote import validar_lote
        itens, recebido, erros = validar_lote(request.form, rodada_sel.jogos, existentes)
        texto_original, jogos_texto = None, set()
        if request.form.get('whatsapp_token'):
            from services.texto_lancamento import ler_assinatura
            from itsdangerous import BadSignature
            try:
                texto_original = ler_assinatura(request.form['whatsapp_token'], current_user.id,
                    bolao.id, participante_id, rodada_id)
                jogos_texto = {int(id) for id in request.form.get('whatsapp_jogos', '').split(',') if id}
                if not jogos_texto or not jogos_texto.issubset({j.id for j in rodada_sel.jogos}):
                    raise ValueError('Jogos inválidos.')
            except (BadSignature, ValueError, TypeError):
                erros['whatsapp'] = 'A prévia da mensagem expirou ou é inválida. Cole e revise a mensagem novamente.'
        if not erros:
            for jogo, casa, fora, primeiro in itens:
                palpite = existentes.get(jogo.id)
                if palpite is None:
                    palpite = Palpite(
                        participante_id=participante_sel.participante_legado_id if bolao else participante_sel.id,
                        participacao_id=participante_sel.id if bolao else None, jogo_id=jogo.id)
                    db.session.add(palpite)
                palpite.situacao = ('nao_enviado' if request.form.get('nao_enviou_rodada') == '1'
                    else request.form.get(f'situacao_{jogo.id}', palpite.situacao or 'valido'))
                palpite.gols_casa = casa
                palpite.gols_fora = fora
                palpite.primeiro_gol = primeiro
                palpite.origem = 'responsavel'
                if recebido is not None:
                    palpite.recebido_em = recebido
                if jogo.id in jogos_texto:
                    palpite._texto_original = texto_original
                    if palpite.id:
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(palpite, 'origem')
            db.session.commit()
            flash(f"{len(itens)} palpites de '{participante_sel.nome}' para a '{rodada_sel.nome}' salvos com sucesso!")
            if bolao:
                lembrar_rodada(bolao, rodada_sel)
                if acao == 'proximo':
                    proximo = proximo_pendente(bolao, rodada_sel, participante_id, participantes)
                    if proximo is None:
                        flash('Todos os participantes elegíveis estão completos nesta rodada.')
                    elif proximo == participante_id:
                        flash('Só este participante ainda tem pendências. Complete os jogos restantes ou revise os palpites guardados.')
                    else:
                        participante_id = proximo
            return redirect(url_for('admin.gerenciar_palpites', participante_id=participante_id, rodada_id=rodada_id))
        valores = request.form
        db.session.rollback()

    rodada_sel = None
    participante_sel = None
    palpites_map = {}

    if rodada_id:
        rodada_sel = Rodada.query.get_or_404(rodada_id)
        validar_rodada(rodada_sel)
        if bolao and not erros:
            lembrar_rodada(bolao, rodada_sel)

    if participante_id:
        participante_sel = pessoa_selecionada(participante_id, rodada_sel)

    if bolao:
        participantes = [p for p in participantes if participa_na_rodada(p, rodada_sel)] if rodada_sel else [p for p in participantes if p.status == 'ativo']

    if rodada_sel and participante_sel:
        palpites = Palpite.query.filter_by(**({'participacao_id': participante_sel.id} if bolao else {'participante_id': participante_sel.id})).all()
        palpites_map = {p.jogo_id: p for p in palpites if p.jogo.rodada_id == rodada_sel.id}

    return render_template(
        "admin_palpites.html",
        participantes=participantes,
        campeonatos=campeonatos,
        rodada_sel=rodada_sel,
        participante_sel=participante_sel,
        palpites_map=palpites_map,
        pontos_por_jogo={id: calcular_pontuacao(p, p.jogo, p.jogo.resultado).total
                        if not p.excluido_por_desistencia else 0 for id, p in palpites_map.items()},
        erros=erros, valores=valores, agora_local=agora_brasilia(),
        rodada_anterior=vizinhos(rodadas, rodada_id)[0],
        rodada_proxima=vizinhos(rodadas, rodada_id)[1],
        pessoa_anterior=vizinhos(participantes, participante_id)[0],
        pessoa_proxima=vizinhos(participantes, participante_id)[1],
        pendentes=participantes_pendentes(bolao, rodada_sel) if bolao and rodada_sel else [],
        rodada_id=rodada_id,
        participante_id=participante_id,
    ), (422 if erros else 200)


# ── Importar planilha do bolão (.xlsx) ────────────────────────────────────────

@admin.route("/importar-planilha", methods=["GET", "POST"])
@admin_required
def importar_planilha():
    from services.importador_planilha import importar_planilha_bolao

    campeonatos = campeonatos_do_contexto()
    pasta = Path(os.environ.get('DOWNLOADS_FOLDER') or Path.home() / 'Downloads').expanduser().resolve()
    planilhas_locais = sorted(str(p.resolve()) for p in pasta.glob('*.xlsx')
                              if p.is_file() and p.resolve().parent == pasta)

    if request.method == 'POST':
        arquivo = request.files.get('arquivo')
        selecionada = request.form.get('planilha_local')
        if arquivo and arquivo.filename:
            valido, msg = validar_arquivo_upload(arquivo.filename, ['xlsx'])
            if not valido:
                flash(msg)
                return redirect(url_for('admin.importar_planilha'))
            # Leitura do stream evita caminhos fornecidos pelo nome do upload.
            origem = arquivo.stream
        elif selecionada in planilhas_locais:
            origem = selecionada
        else:
            flash('Envie um arquivo .xlsx ou selecione uma planilha existente.')
            return redirect(url_for('admin.importar_planilha'))

        if request.form.get('novo_campeonato_nome') or request.form.get('novo_campeonato_ano'):
            abort(400, description="O campeonato deve pertencer ao bolão aberto.")
        try:
            campeonato_id = inteiro(request.form.get('campeonato_id'), 'Campeonato', 1)
            if not any(c.id == campeonato_id for c in campeonatos):
                abort(404)
            if not Bolao.query.filter_by(campeonato_id=campeonato_id).first():
                abort(400, description="Crie primeiro um bolão com seu campeonato.")
        except ValueError as e:
            flash(str(e))
            return redirect(url_for('admin.importar_planilha'))

        try:
            res = importar_planilha_bolao(origem, campeonato_id, commit=False)
            db.session.commit()
            flash(f"Planilha importada com sucesso! {res['participantes_novos']} novos participantes, "
                  f"{res['rodadas']} rodadas, {res['jogos']} jogos e {res['palpites']} palpites cadastrados.")
            return redirect(url_for('admin.listar_campeonatos'))
        except Exception:
            db.session.rollback()
            current_app.logger.exception('Falha na importação de planilha')
            flash('Não foi possível importar a planilha. Confira o formato e os dados do arquivo.')
            return redirect(url_for('admin.importar_planilha'))

    return render_template('admin_importar_planilha.html', campeonatos=campeonatos,
                           planilhas_locais=planilhas_locais)
