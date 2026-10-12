from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from migrations import participacao as migracao


@pytest.fixture
def anterior(tmp_path):
    path = tmp_path / "anterior.db"
    with closing(sqlite3.connect(path)) as con:
        con.executescript(Path(migracao.__file__).with_name("sql").joinpath(
            "001_multi_bolao.sql").read_text(encoding="utf-8"))
        con.executescript("""
            INSERT INTO participante VALUES(1,'Admin','admin@teste.local','hash',1,1,1);
            INSERT INTO campeonato VALUES(1,'Teste',2026,'BSA');
            INSERT INTO rodada VALUES(1,'Rodada 1',1,1);
            INSERT INTO bolao VALUES(1,'Teste',1,1,NULL,0,1,'ativo','2026-01-01',1);
            INSERT INTO participacao VALUES(1,1,NULL,1,'Pessoa','participante','ativo',NULL,1,NULL,NULL,NULL);
            INSERT INTO jogo VALUES(1,'Casa','Fora',0,0,NULL,1,'2026-01-01',NULL,NULL,1);
            INSERT INTO resultado VALUES(1,2,1,NULL,1);
            INSERT INTO palpite VALUES(1,2,1,NULL,1,1,NULL,NULL,NULL,NULL,NULL,0,1,1);
            INSERT INTO palpite_log VALUES(1,1,NULL,'2026-01-01','migracao',NULL,'{}');
            INSERT INTO bonus_rodada VALUES(1,1,1,2,'Credito',1,1);
            INSERT INTO _schema_migrations VALUES('001_multi_bolao','2026-01-01');
        """)
    return path


def test_upgrade_reversao_idempotencia_e_preservacao(anterior):
    antes = migracao.ler(anterior)
    resultado = migracao.upgrade(anterior)
    depois = migracao.ler(anterior)
    assert resultado["pontos_totais"] == 5
    assert migracao.ler(resultado["backup"]) == antes
    migracao.verificar_preservacao(antes, depois)
    part = depois["dados"]["participacao"][0]
    assert part["status"] == "ativo"
    assert all(part[campo] is None for campo in migracao.CAMPOS_PARTICIPACAO)
    assert depois["dados"]["participacao_log"] == []
    assert depois["dados"]["bolao"][0]["politica_entrada_tardia"] == "fora_da_conta"
    assert depois["dados"]["palpite"][0]["excluido_por_desistencia"] == 0
    assert migracao.upgrade(anterior)["status"] == "já migrado"
    migracao.rollback(anterior, resultado["manifesto"])
    assert migracao.ler(anterior) == antes


@pytest.mark.parametrize("sql", [
    "UPDATE palpite SET gols_casa=8",
    "UPDATE participacao SET observacao='Novo dado'",
    "INSERT INTO participacao_log VALUES(1,1,1,'2026-01-01','edicao',NULL,'{}')",
    "UPDATE bolao SET politica_entrada_tardia='zero'",
])
def test_reversao_recusa_descartar_novos_dados(anterior, sql):
    resultado = migracao.upgrade(anterior)
    with closing(sqlite3.connect(anterior)) as con:
        con.execute(sql)
        con.commit()
    antes = migracao.ler(anterior)
    with pytest.raises(ValueError, match="dados novos/alterados"):
        migracao.rollback(anterior, resultado["manifesto"])
    assert migracao.ler(anterior) == antes


def test_falha_no_meio_reverte_ddl_e_dados(anterior, monkeypatch):
    antes = migracao.ler(anterior)
    original = migracao.alterar_schema
    def falhar(con, estado):
        original(con, estado)
        raise ValueError("Falha simulada")
    monkeypatch.setattr(migracao, "alterar_schema", falhar)
    with pytest.raises(ValueError, match="simulada"):
        migracao.upgrade(anterior)
    assert migracao.ler(anterior) == antes


def test_concorrencia_entre_backup_e_lock_recusa(anterior, monkeypatch):
    original = migracao.backup
    def alterar_depois_backup(origem, destino):
        resultado = original(origem, destino)
        with closing(sqlite3.connect(origem)) as con:
            con.execute("UPDATE palpite SET gols_casa=8")
            con.commit()
        return resultado
    monkeypatch.setattr(migracao, "backup", alterar_depois_backup)
    with pytest.raises(ValueError, match="Banco mudou"):
        migracao.upgrade(anterior)
    atual = migracao.ler(anterior)
    assert atual["dados"]["palpite"][0]["gols_casa"] == 8
    assert "participacao_log" not in atual["dados"]


def test_constraints_novas_e_antigas(anterior):
    migracao.upgrade(anterior)
    with closing(sqlite3.connect(anterior)) as con:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("UPDATE participacao SET status='desistente',rodada_desistencia_id=1")
        con.commit()
        for sql in ("UPDATE participacao SET status='inexistente'",
                    "UPDATE participacao SET rodada_entrada_id=999",
                    "UPDATE bolao SET politica_entrada_tardia='invalida'",
                    "UPDATE palpite SET participacao_id=999"):
            with pytest.raises(sqlite3.IntegrityError):
                con.execute(sql)
            con.rollback()


def test_backup_adulterado_e_manifesto_errado(anterior):
    resultado = migracao.upgrade(anterior)
    with pytest.raises(ValueError, match="outro banco"):
        migracao.rollback(anterior.with_name("outro.db"), resultado["manifesto"])
    with closing(sqlite3.connect(resultado["backup"])) as con:
        con.execute("UPDATE palpite SET gols_casa=9")
        con.commit()
    with pytest.raises(ValueError, match="Backup alterado"):
        migracao.rollback(anterior, resultado["manifesto"])


def test_app_recusa_schema_anterior_sem_alterar(anterior):
    from app import create_app
    antes = migracao.ler(anterior)
    with pytest.raises(RuntimeError, match="Migração de participação pendente"):
        create_app("testing", database_uri="sqlite:///" + anterior.as_posix())
    assert migracao.ler(anterior) == antes


def test_cadeia_de_migracoes_desde_legado(tmp_path):
    from tests.test_migracao_fase1 import banco_legado
    from migrations.fase1 import upgrade as fase1
    path = tmp_path / "legado.db"
    banco_legado(path)
    fase1(path)
    antes = migracao.ler(path)
    assert "participacao_log" not in antes["dados"]
    migracao.upgrade(path)
    migracao.verificar_preservacao(antes, migracao.ler(path))
