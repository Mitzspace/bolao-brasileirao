from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database import db
from models import Campeonato, Palpite, Participante, Rodada
from services.pontuacao import calcular_pontos

participante = Blueprint("participante", __name__)


@participante.route("/")
def inicio():
    campeonatos = Campeonato.query.order_by(Campeonato.ano.desc()).all()
    return render_template("index.html", campeonatos=campeonatos)


@participante.route("/jogos")
@participante.route("/jogos/<int:rodada_id>")
def listar_jogos(rodada_id=None):
    campeonatos = Campeonato.query.order_by(Campeonato.ano.desc()).all()
    if not campeonatos:
        return render_template("jogos.html", campeonatos=[], camp_atual=None, rodada_atual=None, jogos=[])

    camp_atual = campeonatos[0]
    rodada_atual = None

    if rodada_id:
        rodada_atual = Rodada.query.get_or_404(rodada_id)
        camp_atual = rodada_atual.campeonato
    else:
        # Prioriza a primeira rodada aberta; se não houver, pega a primeira rodada
        rodada_atual = Rodada.query.filter_by(campeonato_id=camp_atual.id, aberta=True).first()
        if not rodada_atual and camp_atual.rodadas:
            rodada_atual = camp_atual.rodadas[0]

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
    participantes = Participante.query.order_by(Participante.nome).all()
    jogos = rodada.jogos

    from models import Jogo
    palpites_db = Palpite.query.join(Jogo).filter(Jogo.rodada_id == rodada.id).all()
    mapa_palpites = {(p.participante_id, p.jogo_id): p for p in palpites_db}

    matriz = []
    totais_participantes = {p.id: {"pontos": 0, "cravadas": 0} for p in participantes}

    for jogo in jogos:
        res = jogo.resultado
        linha = {
            "jogo": jogo,
            "resultado": res,
            "palpites": {}
        }
        for part in participantes:
            pal = mapa_palpites.get((part.id, jogo.id))
            pts = None
            eh_cravada = False
            eh_vencedor = False

            if pal and res:
                pts = calcular_pontos(pal, res, jogo.especial)
                totais_participantes[part.id]["pontos"] += pts
                if pal.gols_casa == res.gols_casa_real and pal.gols_fora == res.gols_fora_real:
                    eh_cravada = True
                    totais_participantes[part.id]["cravadas"] += 1
                elif pts > 0:
                    eh_vencedor = True

            linha["palpites"][part.id] = {
                "palpite": pal,
                "pontos": pts,
                "cravada": eh_cravada,
                "vencedor": eh_vencedor,
            }
        matriz.append(linha)

    # Adiciona bônus da rodada aos totais
    bonus_db = {b.participante_id: b.pontos for b in rodada.bonus_list}
    for part in participantes:
        b_pts = bonus_db.get(part.id, 0)
        totais_participantes[part.id]["bonus"] = b_pts
        totais_participantes[part.id]["pontos"] += b_pts

    return render_template(
        "grade_palpites.html",
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

    if not rodada.aberta:
        flash("Esta rodada esta fechada para palpites.")
        return redirect(url_for("participante.inicio"))

    if request.method == "POST":

        for jogo in rodada.jogos:

            if jogo.bloqueado():
                continue

            gols_casa = request.form.get(f"casa_{jogo.id}")
            gols_fora = request.form.get(f"fora_{jogo.id}")

            if gols_casa is None or gols_fora is None:
                continue

            primeiro_gol = None
            if jogo.especial:
                primeiro_gol = request.form.get(f"primeiro_{jogo.id}") or None

            palpite = Palpite.query.filter_by(
                participante_id=current_user.id,
                jogo_id=jogo.id,
            ).first()

            if palpite is None:
                palpite = Palpite(
                    participante_id=current_user.id,
                    jogo_id=jogo.id,
                )
                db.session.add(palpite)

            palpite.gols_casa = int(gols_casa)
            palpite.gols_fora = int(gols_fora)
            palpite.primeiro_gol = primeiro_gol

        db.session.commit()
        flash("Palpites enviados!")
        return redirect(url_for("participante.visualizar_rodada", id=rodada.id))

    palpites = Palpite.query.filter_by(participante_id=current_user.id).all()
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

    palpites = Palpite.query.filter_by(participante_id=current_user.id).all()

    itens = []
    for palpite in palpites:
        pontos = None
        if palpite.jogo.resultado:
            pontos = calcular_pontos(palpite, palpite.jogo.resultado, palpite.jogo.especial)
        itens.append({"palpite": palpite, "pontos": pontos})

    itens.sort(key=lambda i: (
        i["palpite"].jogo.rodada.campeonato.nome,
        i["palpite"].jogo.rodada.nome,
        i["palpite"].jogo.id,
    ))

    return render_template("meus_palpites.html", itens=itens)


@participante.route("/ranking")
def ranking():
    todos = Participante.query.all()
    resultado_ranking = []

    for p in todos:
        total_palpites = 0
        cravadas = 0
        acertos_vencedor = 0

        for pal in p.palpites:
            if pal.jogo and pal.jogo.resultado:
                res = pal.jogo.resultado
                pts = calcular_pontos(pal, res, pal.jogo.especial)
                total_palpites += pts

                # Cravada (placar exato)
                if pal.gols_casa == res.gols_casa_real and pal.gols_fora == res.gols_fora_real:
                    cravadas += 1
                elif pts > 0:
                    acertos_vencedor += 1

        total_bonus = sum(b.pontos for b in p.bonus_list)
        total_geral = total_palpites + total_bonus

        resultado_ranking.append({
            "participante": p,
            "pontos": total_geral,
            "pontos_palpites": total_palpites,
            "bonus": total_bonus,
            "cravadas": cravadas,
            "acertos_vencedor": acertos_vencedor,
        })

    # Ordena por pontos totais e desempata por cravadas
    resultado_ranking.sort(key=lambda i: (i["pontos"], i["cravadas"]), reverse=True)

    return render_template("ranking.html", ranking=resultado_ranking)

