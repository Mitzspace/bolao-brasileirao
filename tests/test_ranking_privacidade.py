from datetime import datetime, timedelta
from flask import template_rendered

from database import db
from models import Bolao, Participacao, Palpite, Participante, Resultado


def contextos(app, client, url):
    dados = []
    def capturar(sender, template, context, **extra):
        dados.append(context)
    with template_rendered.connected_to(capturar, app):
        assert client.get(url).status_code == 200
    return dados[0]


def test_grade_oculta_antes_e_mostra_depois(app, client, participante_teste, jogo_teste):
    jogo_teste.data = datetime.now() + timedelta(hours=1)
    db.session.add(Palpite(participante_id=participante_teste.id, jogo_id=jogo_teste.id, gols_casa=8, gols_fora=7))
    db.session.commit()
    url = f"/rodada/{jogo_teste.rodada_id}/palpites"
    from tests.test_seletor_bolao import login
    observador = Participante(nome='Observador', email='observador@example.com')
    db.session.add(Participacao(bolao=Bolao.query.one(), usuario=observador, nome_exibicao='Observador'))
    db.session.commit()
    login(client, observador)
    ctx = contextos(app, client, url)
    assert ctx["matriz"][0]["palpites"][participante_teste.id]["palpite"] is None
    jogo_teste.data = datetime.now() - timedelta(seconds=1)
    db.session.commit()
    ctx = contextos(app, client, url)
    assert ctx["matriz"][0]["palpites"][participante_teste.id]["palpite"].gols_casa == 8


def test_ranking_desempate_e_bonus_nao_conta_acerto(app, client, jogo_teste):
    jogo_teste.especial = True
    db.session.add(Resultado(jogo_id=jogo_teste.id, gols_casa_real=2, gols_fora_real=1, primeiro_gol_real="João"))
    for nome, casa, fora, primeiro in [("Zeca", 3, 1, None), ("Álvaro", 3, 1, None), ("Bia", 0, 1, "João")]:
        pessoa = Participante(nome=nome, email=f"{nome}@example.com")
        db.session.add(pessoa)
        db.session.flush()
        db.session.add(Palpite(participante_id=pessoa.id, jogo_id=jogo_teste.id,
                              gols_casa=casa, gols_fora=fora, primeiro_gol=primeiro))
    db.session.commit()
    from tests.test_seletor_bolao import login
    Palpite.query.filter_by(participante_id=pessoa.id).one().participacao.usuario = pessoa
    db.session.commit()
    login(client, pessoa)
    ranking = contextos(app, client, "/ranking")["ranking"]
    assert [i["participante"].nome for i in ranking] == ["Álvaro", "Zeca", "Bia"]
    assert ranking[2]["pontos"] == 2 and ranking[2]["acertos_vencedor"] == 0


def test_acertos_equivalem_resultados_sem_cravadas_e_visiveis_no_celular(app, client, participante_teste, jogo_teste):
    from models import Jogo
    from tests.test_seletor_bolao import login
    # Cravada, vencedor correto, empate correto, erro e palpite fora do prazo.
    for casa, fora, real_casa, real_fora, situacao in [
        (2, 1, 2, 1, 'valido'), (3, 0, 2, 1, 'valido'),
        (1, 1, 0, 0, 'valido'), (0, 1, 2, 1, 'valido'),
        (3, 0, 2, 1, 'fora_prazo')]:
        jogo = Jogo(time_casa='Casa', time_fora='Fora', rodada=jogo_teste.rodada)
        db.session.add(jogo)
        db.session.flush()
        db.session.add(Resultado(jogo=jogo, gols_casa_real=real_casa, gols_fora_real=real_fora))
        db.session.add(Palpite(participante_id=participante_teste.id, jogo=jogo,
            gols_casa=casa, gols_fora=fora, situacao=situacao))
    db.session.commit()
    part = Participacao.query.filter_by(participante_legado_id=participante_teste.id).one()
    part.usuario = participante_teste
    db.session.commit()
    login(client, participante_teste)
    for url in ['/ranking', f'/ranking?rodada_id={jogo_teste.rodada_id}']:
        item = contextos(app, client, url)['ranking'][0]
        assert item['cravadas'] == 1
        assert item['acertos_vencedor'] == 2
        html = client.get(url).text
        assert '>Acertos</th>' in html
        assert 'hidden sm:table-cell' not in html
