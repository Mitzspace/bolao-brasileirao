import json
from types import SimpleNamespace
import pytest
from tests.apoio_lancamento import enviar
from tests.test_lancamento_rapido import lote, gestao  # noqa: F401
from models import Palpite, PalpiteLog, Resultado
from database import db
from services.pontuacao import calcular_pontuacao
from services.classificacao import nome_time_tabela


def test_ausencia_em_massa_e_correcao(lote):
    client, url, dados, a, b = lote
    assert enviar(client, {**dados, 'nao_enviou_rodada': '1'}).status_code == 200
    assert Palpite.query.count() == 2
    assert all(p.situacao == 'nao_enviado' for p in Palpite.query.all())
    assert PalpiteLog.query.count() == 2
    assert enviar(client, {**dados, f'situacao_{a}': 'valido'}).status_code == 422
    assert enviar(client, {**dados, f'situacao_{a}': 'valido', f'casa_{a}': '2', f'fora_{a}': '1'}).status_code == 200
    assert Palpite.query.filter_by(jogo_id=a).one().situacao == 'valido'
    assert Palpite.query.filter_by(jogo_id=b).one().situacao == 'nao_enviado'


def test_atraso_anula_pontos_e_audita(lote):
    client, url, dados, a, b = lote
    assert enviar(client, {**dados, f'casa_{a}': '2', f'fora_{a}': '1'}).status_code == 200
    p = Palpite.query.one()
    db.session.add(Resultado(jogo_id=a, gols_casa_real=2, gols_fora_real=1))
    db.session.commit()
    assert calcular_pontuacao(p, p.jogo, p.jogo.resultado).total > 0
    assert enviar(client, {**dados, f'situacao_{a}': 'fora_prazo'}).status_code == 200
    assert calcular_pontuacao(p, p.jogo, p.jogo.resultado).total == 0
    assert json.loads(PalpiteLog.query.order_by(PalpiteLog.id.desc()).first().valores_novos)['situacao'] == 'fora_prazo'
    tela = client.get(f"/interface/api/palpites?rodada_id={dados['rodada_id']}&participacao_id={dados['participante_id']}").get_json()
    palpite = next(j for j in tela['jogos'] if j['id'] == a)['palpite']
    assert palpite['situacao'] == 'fora_prazo' and palpite['pontos'] == 0


def test_situacao_invalida_nao_grava(lote):
    client, url, dados, a, b = lote
    assert enviar(client, {**dados, f'situacao_{a}': 'invalido', f'casa_{b}': '1', f'fora_{b}': '0'}).status_code == 422
    assert Palpite.query.count() == 0


@pytest.mark.parametrize('nome,esperado', [('Mineiro', 'Atlético-MG'), ('Paranaense', 'Atlético Paranaense')])
def test_nomes_solicitados(nome, esperado):
    assert nome_time_tabela({'shortName': nome}, 'BSA') == esperado
    assert nome_time_tabela({'shortName': nome}, 'PL') == nome


def test_migracao_idempotente_com_backup(tmp_path):
    import sqlite3
    from migrations.situacao_palpite import migrar
    path = tmp_path / 'teste.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE palpite (id INTEGER PRIMARY KEY)')
        con.execute('INSERT INTO palpite VALUES (1)')
    backup = migrar(path)
    assert backup.exists() and migrar(path) is None
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT situacao FROM palpite').fetchone()[0] == 'valido'


def test_worker_chama_sync_com_temporada_e_isola_falha(app, monkeypatch):
    from models import Campeonato, Rodada
    from services.sync_automatico import sincronizar_ciclo
    for ano in (2025, 2026):
        c = Campeonato(nome=str(ano), ano=ano, codigo_api='BSA')
        db.session.add(c)
        db.session.flush()
        db.session.add(Rodada(nome='Rodada 1', campeonato_id=c.id))
    db.session.commit()
    chamadas = []
    def fake(token, codigo, temporada):
        chamadas.append(temporada)
        if temporada == 2025:
            raise RuntimeError('API indisponível')
        return {}
    monkeypatch.setattr('services.sync_automatico.sync_competicao', fake)
    app.config['FOOTBALL_DATA_TOKEN'] = 'teste'
    sincronizar_ciclo(app)
    assert chamadas == [2025, 2026]
