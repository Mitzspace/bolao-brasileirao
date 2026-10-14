"""Operação específica e idempotente: backup integral, validação e mesclagem 25 -> 4."""
import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text
from scripts.inspecionar_albert import engine_publicado
from services.mesclagem_participantes import mesclar_sem_palpites


def executar():
    with engine_publicado().begin() as con:
        con.execute(text("SET LOCAL lock_timeout = '10s'"))
        tabelas = con.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
        nomes = [con.dialect.identifier_preparer.quote(t) for t in tabelas]
        con.execute(text('LOCK TABLE ' + ', '.join(nomes) + ' IN SHARE ROW EXCLUSIVE MODE'))
        registros = con.execute(text('SELECT id,nome_exibicao FROM participacao WHERE id IN (4,25) ORDER BY id')).all()
        if registros == [(4, 'Albert')]:
            print('Albert já mesclado; nenhuma alteração.')
            return
        if registros != [(4, 'Albert(original)'), (25, 'Albert(admin)')]:
            raise ValueError('Os registros mudaram desde a inspeção. Revise antes de continuar.')
        backup = {t: [dict(r) for r in con.execute(text(f'SELECT * FROM {q}')).mappings()]
                  for t, q in zip(tabelas, nomes)}
        pasta = Path('instance/backups')
        pasta.mkdir(exist_ok=True)
        path = pasta / ('neon-antes-mesclar-albert-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + '.json')
        with path.open('x', encoding='utf-8') as arquivo:
            json.dump(backup, arquivo, ensure_ascii=False, default=str)
        assert json.loads(path.read_text(encoding='utf-8')).keys() == backup.keys()
        con.execute(text('ALTER TABLE participacao ADD COLUMN IF NOT EXISTS email VARCHAR(100)'))
        mesclar_sem_palpites(con, 25, 4, 'Albert')
        con.execute(text('''UPDATE participacao p SET email=lower(trim(u.email))
            FROM participante u WHERE p.usuario_id=u.id AND p.email IS NULL'''))
        for tabela in ('palpite', 'bonus_rodada', 'palpite_log', 'participante'):
            assert con.execute(text(f'SELECT count(*) FROM {tabela}')).scalar() == len(backup[tabela])
        assert con.execute(text('SELECT count(*) FROM participacao')).scalar() == len(backup['participacao']) - 1
        assert con.execute(text('SELECT count(*) FROM participacao_log')).scalar() == len(backup['participacao_log']) + 1
        con.execute(text('SET CONSTRAINTS ALL IMMEDIATE'))
        print('Backup:', path)
    print('Mesclagem confirmada: Albert #4, conta #45, responsável; palpites, bônus e logs preservados.')


if __name__ == '__main__':
    executar()
