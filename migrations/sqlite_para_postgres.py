"""Importação única, transacional, para um schema public vazio; origem intacta."""
import argparse
from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from sqlalchemy import Boolean, DateTime, Integer, String, create_engine, select, text
from sqlalchemy.pool import NullPool

from config import normalizar_database_url
from database import db
import models  # registra todas as tabelas, sem criar app ou executar eventos ORM
from services.operacao import backup_sqlite


class ErroMigracao(ValueError):
    pass


def converter(coluna, valor):
    """Recusa valores que SQLite tolera e PostgreSQL não; nunca trunca dados."""
    if valor is None:
        if not coluna.nullable:
            raise ErroMigracao(f'{coluna.table.name}.{coluna.name}: NULL não permitido.')
        return None
    if isinstance(coluna.type, Boolean):
        if type(valor) is not int or valor not in (0, 1):
            raise ErroMigracao(f'{coluna.table.name}.{coluna.name}: booleano inválido.')
        return bool(valor)
    if isinstance(coluna.type, DateTime):
        try:
            data = datetime.fromisoformat(valor)
            if data.tzinfo is not None:
                raise ValueError()
            return data
        except (TypeError, ValueError):
            raise ErroMigracao(f'{coluna.table.name}.{coluna.name}: data inválida/ambígua.') from None
    if isinstance(coluna.type, Integer):
        if type(valor) is not int or not -(2**31) <= valor < 2**31:
            raise ErroMigracao(f'{coluna.table.name}.{coluna.name}: inteiro inválido.')
    if isinstance(coluna.type, String):
        if (not isinstance(valor, str) or '\x00' in valor
                or (coluna.type.length and len(valor) > coluna.type.length)):
            raise ErroMigracao(f'{coluna.table.name}.{coluna.name}: texto incompatível, revise sem truncar.')
    return valor


def carregar_snapshot(caminho):
    """Lê uma cópia consistente em modo somente leitura; não acessa o destino."""
    uri = Path(caminho).resolve(strict=True).as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as con:
        con.row_factory = sqlite3.Row
        if con.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or con.execute('PRAGMA foreign_key_check').fetchall():
            raise ErroMigracao('SQLite falhou na verificação de integridade/referências.')
        existentes = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        esperadas = set(db.metadata.tables)
        # Histórico de migrações antigas fica preservado no backup SQLite.
        if existentes - esperadas - {'_schema_migrations'}:
            raise ErroMigracao('SQLite contém tabelas desconhecidas; revise antes de migrar.')
        if esperadas - existentes:
            raise ErroMigracao('Schema SQLite incompleto. Atualize uma cópia usando as migrações documentadas.')
        dados = {}
        for tabela in db.metadata.sorted_tables:
            colunas = {r[1] for r in con.execute(f'PRAGMA table_info("{tabela.name}")')}
            if colunas != set(tabela.columns.keys()):
                raise ErroMigracao(f'Schema de {tabela.name} incompatível; revise as migrações SQLite.')
            dados[tabela.name] = [
                {c.name: converter(c, row[c.name]) for c in tabela.columns}
                for row in con.execute(f'SELECT * FROM "{tabela.name}" ORDER BY id')]
    return dados


def resumo(dados):
    resultado = {}
    for nome, linhas in dados.items():
        serializado = json.dumps(linhas, sort_keys=True, ensure_ascii=False,
            separators=(',', ':'), default=lambda v: v.isoformat(timespec='microseconds'))
        resultado[nome] = {'registros': len(linhas),
                          'sha256': hashlib.sha256(serializado.encode()).hexdigest()}
    return resultado


def importar(dados, engine):
    """DDL, registros, sequência e verificação na mesma transação PostgreSQL."""
    if engine.dialect.name != 'postgresql':
        raise ErroMigracao('O destino deve ser PostgreSQL.')
    esperado = resumo(dados)
    with engine.begin() as con:
        con.execute(text("SET LOCAL lock_timeout = '15s'"))
        con.execute(text("SET LOCAL statement_timeout = '120s'"))
        con.execute(text('SELECT pg_advisory_xact_lock(208461017)'))
        # Nada é apagado. Recusa até schema previamente inicializado vazio.
        if con.execute(text("SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                            "WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S') LIMIT 1")).first():
            raise ErroMigracao('Destino não vazio. Use banco/branch novo; nenhuma tabela foi sobrescrita.')
        con.execute(text('SET LOCAL search_path TO public'))
        db.metadata.create_all(con)
        for tabela in db.metadata.sorted_tables:
            linhas = dados[tabela.name]
            for inicio in range(0, len(linhas), 500):
                con.execute(tabela.insert(), linhas[inicio:inicio + 500])
            sequencia = con.execute(text('SELECT pg_get_serial_sequence(:tabela, :coluna)'),
                {'tabela': 'public.' + tabela.name, 'coluna': 'id'}).scalar_one()
            if sequencia:
                proximo = max((r['id'] for r in linhas), default=0) + 1
                # ALTER SEQUENCE é transacional; identificador vem do catálogo, não do usuário.
                partes = sequencia.split('.')
                identificador = '.'.join(con.dialect.identifier_preparer.quote(p) for p in partes)
                con.execute(text(f'ALTER SEQUENCE {identificador} RESTART WITH {max(1, proximo)}'))
        obtido = {t.name: [dict(r) for r in con.execute(select(t).order_by(t.c.id)).mappings()]
                  for t in db.metadata.sorted_tables}
        if resumo(obtido) != esperado:
            raise ErroMigracao('Verificação de conteúdo falhou; importação revertida.')
    return esperado


def main():
    from dotenv import load_dotenv
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origem', type=Path)
    parser.add_argument('--backup', type=Path, required=True, help='Novo arquivo SQLite; nunca sobrescrito')
    parser.add_argument('--aplicar', action='store_true', help='Sem esta opção apenas valida o backup local')
    parser.add_argument('--env-file', type=Path, help='Arquivo privado com MIGRATION_DATABASE_URL')
    args = parser.parse_args()
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('Arquivo privado não encontrado.')
        load_dotenv(args.env_file, override=True)
    try:
        backup_sqlite(args.origem, args.backup)
        dados = carregar_snapshot(args.backup)
        relatorio = resumo(dados)
        if args.aplicar:
            url = os.environ.get('MIGRATION_DATABASE_URL', '')
            if not url:
                raise ErroMigracao('Configure MIGRATION_DATABASE_URL com a URL direta do destino.')
            engine = create_engine(normalizar_database_url(url, exigir_tls=True),
                poolclass=NullPool, hide_parameters=True,
                connect_args={'connect_timeout': 15, 'prepare_threshold': None})
            try:
                relatorio = importar(dados, engine)
            finally:
                engine.dispose()
        print(json.dumps({'aplicado': args.aplicar, 'tabelas': relatorio}, indent=2))
    except ErroMigracao as exc:
        parser.exit(1, str(exc) + '\n')
    except Exception:
        # Drivers podem incluir dados pessoais, SQL e senha na exceção.
        parser.exit(1, 'Migração não concluída. Verifique configuração, backup exclusivo, conexão e constraints. '
                       'Nenhum registro existente no destino foi substituído. Não publique antes de validar.\n')


if __name__ == '__main__':
    main()
