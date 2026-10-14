from io import BytesIO

import openpyxl
import pytest

from database import db
from models import BonusRodada, Campeonato, Jogo, Palpite, Participante, Resultado
from services.importador_planilha import importar_planilha_bolao
from services.importacao_cli import importar


def planilha(bonus=3):
    wb = openpyxl.Workbook()
    rodada = wb.active
    rodada.title = '1ª Rodada'
    rodada.append(['Jogo', 'Pessoa Nova'])
    rodada.append(['Time A x Time B ★ [2x1]', '2x1'])
    rodada.append(['Time C 0x0 Time D', '1x1'])
    total = wb.create_sheet('TOTAL')
    total.append(['Rodada', 'Pessoa Nova'])
    total.append(['BÔNUS'])
    total.append(['1ª Rodada', bonus])
    stream = BytesIO()
    wb.save(stream)
    wb.close()
    stream.seek(0)
    return stream


def test_importacao_compartilhada_repetida_e_bonus(app, campeonato_teste):
    for _ in range(2):
        importar_planilha_bolao(planilha(), campeonato_teste.id, importar_bonus=True)
    assert Jogo.query.count() == 2
    assert Palpite.query.count() == 2
    assert Resultado.query.count() == 2
    assert BonusRodada.query.one().pontos == 3
    assert Jogo.query.filter_by(time_casa='Time A').one().classico
    assert not Participante.query.filter_by(nome='Pessoa Nova').one().conta_ativa


def test_falha_no_bonus_reverte_toda_importacao(app, campeonato_teste):
    with pytest.raises(ValueError):
        importar_planilha_bolao(planilha('invalido'), campeonato_teste.id, importar_bonus=True)
    assert Jogo.query.count() == Palpite.query.count() == Participante.query.count() == 0
    assert Campeonato.query.count() == 1


def test_cli_preserva_campeonato_existente_e_recusa_repeticao(app, admin_teste, campeonato_teste, tmp_path):
    admin_teste.admin_global = True
    db.session.commit()
    arquivo = tmp_path / 'dados.xlsx'
    arquivo.write_bytes(planilha().getvalue())
    importar(arquivo, admin_teste.email, 'Novo', 2026, importar_bonus=True)
    assert Campeonato.query.count() == 2
    assert db.session.get(Campeonato, campeonato_teste.id).nome == 'Campeonato Teste'
    assert BonusRodada.query.one().pontos == 3
    with pytest.raises(ValueError, match='já existem'):
        importar(arquivo, admin_teste.email, 'Novo', 2026)
    assert Campeonato.query.count() == 2


def test_cli_recusa_arquivo_inexistente_sem_mudar_banco(app, admin_teste, campeonato_teste, tmp_path):
    with pytest.raises(ValueError, match='existente'):
        importar(tmp_path / 'ausente.xlsx', admin_teste.email, 'Novo', 2026)
    assert Campeonato.query.count() == 1
