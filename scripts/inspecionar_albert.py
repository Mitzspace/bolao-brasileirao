"""Diagnóstico somente leitura dos registros Albert no banco publicado."""
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from config import normalizar_database_url


def engine_publicado():
    return create_engine(normalizar_database_url(dotenv_values('.env.neon.local')['DATABASE_URL']),
                         connect_args={'connect_timeout': 15}, pool_pre_ping=True)


if __name__ == '__main__':
    with engine_publicado().connect() as con:
        con.execute(text('SET TRANSACTION READ ONLY'))
        rows = con.execute(text("""
            SELECT p.*, (SELECT count(*) FROM palpite WHERE participacao_id=p.id) AS palpites,
            (SELECT count(*) FROM bonus_rodada WHERE participacao_id=p.id) AS bonus,
            (SELECT count(*) FROM participacao_log WHERE participacao_id=p.id) AS logs
            FROM participacao p WHERE lower(nome_exibicao) LIKE '%albert%' ORDER BY id
        """)).mappings().all()
        for row in rows:
            print(dict(row))
        print('Referências:', con.execute(text("""
            SELECT tc.table_name,kcu.column_name,ccu.table_name AS destino
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name AND ccu.table_schema=tc.table_schema
            WHERE tc.constraint_type='FOREIGN KEY' AND ccu.table_name IN ('participacao','participante')
        """)).all())
