from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload, selectinload
from services.validacao_formularios import placar

from database import db
from models import Bolao, BonusRodada, Campeonato, ClassificacaoCache, Jogo, Palpite, Participante, Participacao, Rodada
from services.contexto_bolao import (bolao_atual, campeonatos_do_contexto,
    destino_troca_bolao, lembrar_bolao, minha_participacao, opcoes_rodadas, ordem_rodada, responsavel_atual, validar_rodada)
from services.pontuacao import calcular_pontuacao
from services.classificacao import buscar_classificacao
from services.elegibilidade import (participa_na_rodada, entra_no_ranking_da_rodada,
                                    palpite_elegivel, dentro_do_periodo)

participante = Blueprint("participante", __name__)


def _relacoes_participacao():
    return (joinedload(Participacao.bolao), joinedload(Participacao.rodada_entrada),
            joinedload(Participacao.rodada_desistencia))


def _relacoes_palpite():
    return (joinedload(Palpite.jogo).joinedload(Jogo.resultado),
            joinedload(Palpite.jogo).joinedload(Jogo.rodada).joinedload(Rodada.campeonato),
            joinedload(Palpite.participacao).options(*_relacoes_participacao()))


@participante.route('/boloes/novo', methods=['GET', 'POST'])
@login_required
def criar_bolao():
    from services.acesso import pode_acessar_gestao
    from services.responsaveis import bloquear_bolao
    if not pode_acessar_gestao(current_user):
        abort(403)
    fontes = (Bolao.query.join(Participacao).filter(
        Participacao.usuario_id == current_user.id, Participacao.papel == 'responsavel',
        Participacao.status == 'ativo').order_by(Bolao.nome, Bolao.id).all())
    valores = request.form if request.method == 'POST' else request.args
    origem_id = valores.get('origem_id', '').strip()
    origem = None
    if origem_id:
        if len(valores.getlist('origem_id')) != 1 or not origem_id.isdecimal():
            abort(400)
        origem = next((b for b in fontes if b.id == int(origem_id)), None)
        if origem is None:
            abort(403)
    pessoas = (Participacao.query.filter(Participacao.bolao_id == origem.id,
        (Participacao.usuario_id.is_(None) | (Participacao.usuario_id != current_user.id)))
        .order_by(Participacao.nome_exibicao, Participacao.id).all()) if origem else []
    erro = None
    marcados = valores.getlist('participacao_ids')
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        from services.validacao_formularios import texto, inteiro
        campeonato = None
        if not 2 <= len(nome) <= 100:
            erro = 'Informe um nome entre 2 e 100 caracteres.'
        elif request.form.get('campeonato_id'):
            erro = 'Informe o campeonato deste novo bolão; não selecione um campeonato de outro bolão.'
        else:
            try:
                campeonato_nome = texto(request.form.get('campeonato_nome'), 'Campeonato')
                campeonato_ano = inteiro(request.form.get('campeonato_ano'), 'Temporada', 1, 9999)
                codigo_api = texto(request.form.get('codigo_api') or 'BSA', 'Código da API', 20).upper()
            except ValueError as e:
                erro = str(e)
        if any(not id.isdecimal() for id in marcados):
            abort(400)
        selecionados = {int(id) for id in marcados}
        if selecionados - {p.id for p in pessoas}:
            abort(403)
        if erro is None:
            if origem:
                # Revalida o acesso à fonte sob o mesmo bloqueio usado na revogação.
                bloquear_bolao(origem.id)
            campeonato = Campeonato(nome=campeonato_nome, ano=campeonato_ano, codigo_api=codigo_api)
            novo = Bolao(nome=nome, campeonato=campeonato, criador=current_user,
                         permite_palpite_proprio=False, permite_lancamento_por_responsavel=True)
            db.session.add(novo)
            db.session.add(Participacao(bolao=novo, usuario=current_user,
                nome_exibicao=current_user.nome, papel='responsavel', status='ativo'))
            for pessoa in pessoas:
                if pessoa.id in selecionados:
                    db.session.add(Participacao(bolao=novo, nome_exibicao=pessoa.nome_exibicao,
                        papel='participante', status='ativo'))
            db.session.commit()
            lembrar_bolao(novo.id)
            flash(f'Bolão criado com {len(selecionados)} participantes copiados, além do responsável.')
            return redirect(url_for('admin.listar_participantes', bolao_id=novo.id))
    return render_template('criar_bolao.html', fontes=fontes, origem=origem, pessoas=pessoas,
        erro=erro, valores=valores, marcados=marcados), (400 if erro else 200)


@participante.route('/boloes')
@login_required
def escolher_bolao():
    if (request.args.get('continuar') == '1' and bolao_atual()
            and (current_app.config['FEATURE_PARTICIPANTE_LOGIN']
                 or len(g.boloes_disponiveis) == 1)):
        return redirect(url_for('participante.inicio', bolao_id=bolao_atual().id))
    from services.resumo_boloes import resumos_boloes
    return render_template('escolher_bolao.html', resumos=resumos_boloes(g.boloes_disponiveis))


@participante.route('/boloes/selecionar', methods=['POST'])
@login_required
def selecionar_bolao():
    escolhido = request.form.get('bolao_id', type=int)
    bolao = next((b for b in g.boloes_disponiveis if b.id == escolhido), None)
    if bolao is None:
        abort(403)
    destino = destino_troca_bolao(bolao, request.form)
    lembrar_bolao(escolhido)
    return redirect(destino)


@participante.route("/")
def inicio():
    campeonatos = campeonatos_do_contexto()
    return render_template("index.html", campeonatos=campeonatos)


@participante.route("/jogos")
@participante.route("/jogos/<int:rodada_id>")
def listar_jogos(rodada_id=None):
    campeonatos = campeonatos_do_contexto()
    if not campeonatos:
        return render_template("jogos.html", campeonatos=[], camp_atual=None, rodada_atual=None, jogos=[])

    camp_atual = campeonatos[0]
    rodada_atual = None

    if rodada_id:
        rodada_atual = Rodada.query.get_or_404(rodada_id)
        validar_rodada(rodada_atual)
        camp_atual = rodada_atual.campeonato
    else:
        from services.resumo_boloes import rodadas_de_referencia
        rodada_atual = rodadas_de_referencia({camp_atual.id})[camp_atual.id]['rodada']

    jogos = rodada_atual.jogos if rodada_atual else []

    return render_template(
        "jogos.html",
        campeonatos=campeonatos,
        camp_atual=camp_atual,
        rodada_atual=rodada_atual,
        jogos=jogos,
    )


@participante.route("/rodada/<int:id>/palpites")
def ver_grade_palpites(id):
    rodada = Rodada.query.get_or_404(id)
    validar_rodada(rodada)
    bolao = bolao_atual()
    from services.grade_palpites import montar_grade
    participantes, jogos, matriz, totais_participantes, bonus_db = montar_grade(bolao, rodada)

    from services.textos_whatsapp import texto_rodada
    return render_template(
        "grade_palpites.html",
        texto_copiavel=(texto_rodada(
            bolao, rodada, matriz, participantes, totais_participantes) if bolao and responsavel_atual() else None),
        rodada=rodada,
        jogos=jogos,
        participantes=participantes,
        matriz=matriz,
        totais=totais_participantes,
        bonus_map=bonus_db,
    )




@participante.route("/rodada/<int:id>", methods=["GET", "POST"])
@login_required
def visualizar_rodada(id):

    rodada = Rodada.query.get_or_404(id)
    validar_rodada(rodada)
    part = minha_participacao()
    if bolao_atual() and (not part or not participa_na_rodada(part, rodada)):
        abort(403)

    if not rodada.aberta:
        flash("Esta rodada esta fechada para palpites.")
        return redirect(url_for("participante.inicio"))

    if request.method == "POST":

        if bolao_atual() and 'bolao_id' in request.form and request.form.get('bolao_id', type=int) != bolao_atual().id:
            abort(403)

        # Valida o lote inteiro antes de criar/alterar qualquer palpite.
        entradas = []
        for jogo in rodada.jogos:

            if jogo.bloqueado():
                continue

            gols_casa = request.form.get(f"casa_{jogo.id}")
            gols_fora = request.form.get(f"fora_{jogo.id}")

            if gols_casa is None and gols_fora is None:
                continue

            try:
                gc, gf = placar(gols_casa, gols_fora)
            except ValueError as e:
                flash(str(e))
                return redirect(url_for('participante.visualizar_rodada', id=rodada.id))
            entradas.append((jogo, gc, gf))

        for jogo, gols_casa, gols_fora in entradas:

            primeiro_gol = None
            if jogo.especial:
                primeiro_gol = request.form.get(f"primeiro_{jogo.id}") or None

            palpite = Palpite.query.filter_by(
                **({'participacao_id': part.id} if part else {'participante_id': current_user.id}),
                jogo_id=jogo.id,
            ).first()

            if palpite is None:
                palpite = Palpite(
                    participante_id=part.participante_legado_id if part else current_user.id,
                    participacao_id=part.id if part else None,
                    jogo_id=jogo.id,
                )
                db.session.add(palpite)

            palpite.gols_casa = gols_casa
            palpite.gols_fora = gols_fora
            palpite.primeiro_gol = primeiro_gol

        db.session.commit()
        flash("Palpites enviados!")
        return redirect(url_for("participante.visualizar_rodada", id=rodada.id))

    palpites = Palpite.query.filter_by(**({'participacao_id': part.id} if part else {'participante_id': current_user.id})).all()
    palpites_por_jogo = {p.jogo_id: p for p in palpites}
    jogos_bloqueados = {jogo.id: jogo.bloqueado() for jogo in rodada.jogos}

    return render_template(
        "rodada.html",
        rodada=rodada,
        palpites=palpites_por_jogo,
        jogos_bloqueados=jogos_bloqueados,
    )


@participante.route("/meus-palpites")
@login_required
def meus_palpites():
    part = minha_participacao()
    opcoes = opcoes_rodadas(bolao_atual().campeonato_id)
    pendentes = {id for (id,) in db.session.query(Jogo.rodada_id).join(Rodada).filter(
        Rodada.campeonato_id == bolao_atual().campeonato_id, Jogo.encerrado.is_(False)).distinct().all()}
    padrao = next((r for r, _ in opcoes if r.id in pendentes), opcoes[-1][0] if opcoes else None)
    selecionada = padrao
    if 'rodada' in request.args:
        selecionada = next((r for r, chave in opcoes if chave == request.args.get('rodada')), None)
        if selecionada is None or len(request.args.getlist('rodada')) != 1:
            abort(404)
    indice = next((i for i, (r, _) in enumerate(opcoes) if r == selecionada), None)
    chave_atual = opcoes[indice][1] if indice is not None else None
    palpites = (Palpite.query.options(*_relacoes_palpite()).join(Jogo).filter(Palpite.participacao_id == part.id,
        Jogo.rodada_id == selecionada.id).all() if selecionada and part else [])

    itens = []
    for palpite in palpites:
        pontos = None
        if palpite.jogo.resultado:
            pontos = calcular_pontuacao(palpite, palpite.jogo, palpite.jogo.resultado).total
        itens.append({"palpite": palpite, "pontos": pontos})

    itens.sort(key=lambda i: (
        i["palpite"].jogo.rodada.campeonato.nome,
        ordem_rodada(i["palpite"].jogo.rodada),
        i["palpite"].jogo.id,
    ))

    return render_template("meus_palpites.html", itens=itens, opcoes_rodadas=opcoes,
        rodada_selecionada=selecionada, rodada_chave=chave_atual,
        rodada_anterior=opcoes[indice - 1][1] if indice is not None and indice > 0 else None,
        rodada_proxima=opcoes[indice + 1][1] if indice is not None and indice + 1 < len(opcoes) else None)


@participante.route("/ranking")
def ranking():
    bolao = bolao_atual()
    opcoes = opcoes_rodadas(bolao.campeonato_id) if bolao else []
    rodada_selecionada = None
    if len(request.args.getlist('rodada_id')) > 1:
        abort(404)
    if request.args.get('rodada_id'):
        rodada_id = request.args.get('rodada_id', type=int)
        rodada_selecionada = next((r for r, _ in opcoes if r.id == rodada_id), None)
        if rodada_selecionada is None:
            abort(404)
    ocultar_desistentes = request.args.get('ocultar_desistentes') == '1'
    from services.ranking import calcular_ranking
    resultado_ranking = calcular_ranking(bolao, rodada_selecionada, ocultar_desistentes)

    from services.textos_whatsapp import texto_ranking
    return render_template("ranking.html", ranking=resultado_ranking, opcoes_rodadas=opcoes,
        ocultar_desistentes=ocultar_desistentes,
        rodada_selecionada=rodada_selecionada,
        texto_copiavel=texto_ranking(bolao, resultado_ranking, rodada_selecionada)
            if bolao and responsavel_atual() else None)


@participante.route("/tabela")
def tabela():
    """Exibe a classificação do campeonato consultando a API football-data.org com cache de 15 min."""
    import os

    campeonatos = campeonatos_do_contexto()

    # Seleciona o campeonato: por query-string ou o mais recente
    camp_id = request.args.get("campeonato_id", type=int)
    camp_atual = next((c for c in campeonatos if c.id == camp_id), None) if camp_id else None
    if camp_id and camp_atual is None:
        abort(404)

    if not camp_atual and campeonatos:
        camp_atual = campeonatos[0]

    if not camp_atual:
        return render_template(
            "tabela.html",
            campeonatos=campeonatos,
            camp_atual=None,
            resultado=None,
        )

    token = current_app.config.get("FOOTBALL_DATA_TOKEN") or os.environ.get("FOOTBALL_DATA_TOKEN")
    competicao = (camp_atual.codigo_api or "BSA").strip().upper()
    temporada = str(camp_atual.ano) if camp_atual.ano else None

    resultado = buscar_classificacao(
        token=token,
        competicao=competicao,
        temporada=temporada,
        campeonato_id=camp_atual.id,
    )

    return render_template(
        "tabela.html",
        campeonatos=campeonatos,
        camp_atual=camp_atual,
        resultado=resultado,
    )
