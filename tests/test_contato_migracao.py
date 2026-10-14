import sqlite3

from migrations.contato_participante import migrar


def test_migracao_contato_preserva_dados_e_backup(tmp_path):
    path = tmp_path / 'banco.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE participacao (id INTEGER PRIMARY KEY, nome_exibicao TEXT)')
        con.execute("INSERT INTO participacao VALUES (4, 'Albert')")
    backup = migrar(path)
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT * FROM participacao').fetchall() == [(4, 'Albert', None)]
    with sqlite3.connect(backup) as con:
        assert con.execute('SELECT * FROM participacao').fetchall() == [(4, 'Albert')]
    assert migrar(path) is None
