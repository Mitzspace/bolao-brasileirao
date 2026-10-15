"""Classificação: desempate, cravadas/resultados e isolamento entre bolões do mesmo campeonato."""
from datetime import datetime, timedelta

from database import db
from models import Jogo, Palpite, Participacao, Participante, Resultado
from services.ranking import calcular_ranking
from tests.apoio import estrutura, login


def test_ranking_desempate_e_bonus_nao_conta_acerto(app, jogo_teste):
    jogo_teste.especial = True
    db.session.add(Resultado(jogo_id=jogo_teste.id, gols_casa_real=2, gols_fora_real=1, primeiro_gol_real="João"))
    for nome, casa, fora, primeiro in [("Zeca", 3, 1, None), ("Álvaro", 3, 1, None), ("Bia", 0, 1, "João")]:
        pessoa = Participante(nome=nome, email=f"{nome}@example.com")
        db.session.add(pessoa)
        db.session.flush()
        db.session.add(Palpite(participante_id=pessoa.id, jogo_id=jogo_teste.id,
                               gols_casa=casa, gols_fora=fora, primeiro_gol=primeiro))
    db.session.commit()
    bolao = Palpite.query.first().participacao.bolao
    ranking = calcular_ranking(bolao)
    assert [i["participante"].nome for i in ranking] == ["Álvaro", "Zeca", "Bia"]
    assert ranking[2]["pontos"] == 2 and ranking[2]["acertos_vencedor"] == 0


def test_resultados_sem_cravadas_e_fora_do_prazo(app, participante_teste, jogo_teste):
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
    for rodada in (None, jogo_teste.rodada):
        item = calcular_ranking(part.bolao, rodada)[0]
        assert item['cravadas'] == 1 and item['acertos_vencedor'] == 2


def test_dois_boloes_mesmo_campeonato_separam_palpites_ranking_grade(client, participante_teste, jogo_teste):
    a, pa = estrutura(participante_teste, jogo_teste.rodada.campeonato, 'Brasileirão 2026')
    b, pb = estrutura(participante_teste, jogo_teste.rodada.campeonato, 'Brasileirão 2026')
    jogo_teste.data = datetime.now() - timedelta(days=1)
    db.session.add_all([Resultado(jogo=jogo_teste, gols_casa_real=1, gols_fora_real=0),
                        Palpite(participacao=pa, jogo=jogo_teste, gols_casa=1, gols_fora=0),
                        Palpite(participacao=pb, jogo=jogo_teste, gols_casa=0, gols_fora=2)])
    db.session.commit()
    login(client, participante_teste)
    for bolao, part, pontos in [(a, pa, 3), (b, pb, 0), (a, pa, 3)]:
        assert client.post('/interface/selecionar', data={'bolao_id': bolao.id}).status_code == 303
        rank = client.get(f'/interface/api/boloes/{bolao.id}/classificacao').get_json()['ranking']
        assert len(rank) == 1 and rank[0]['participacaoId'] == part.id and rank[0]['pontos'] == pontos
        grade = client.get(f'/interface/api/rodadas/{jogo_teste.rodada_id}/grade').get_json()
        assert [p['id'] for p in grade['participantes']] == [part.id]
        tela = client.get(f'/interface/api/palpites?rodada_id={jogo_teste.rodada_id}&participacao_id={part.id}').get_json()
        assert tela['pessoa']['id'] == part.id
    client.post('/interface/api/palpites', json={'participacaoId': pa.id, 'rodadaId': jogo_teste.rodada_id,
                                                 'jogos': {str(jogo_teste.id): {'casa': '4', 'fora': '0'}}})
    assert Palpite.query.filter_by(participacao_id=pa.id).one().gols_casa == 4
    assert Palpite.query.filter_by(participacao_id=pb.id).one().gols_casa == 0
