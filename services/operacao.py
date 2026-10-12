"""Operações administrativas disponíveis apenas pelo terminal do servidor."""
from contextlib import closing
from pathlib import Path
import sqlite3

import click
from flask.cli import with_appcontext
from database import db
from models import Participante
from utils import hash_senha, validar_email


def backup_sqlite(origem, destino):
    origem = Path(origem).resolve(strict=True)
    destino = Path(destino).resolve()
    # Nunca sobrescreve um banco ou backup anterior.
    with destino.open('xb'):
        pass
    with closing(sqlite3.connect(origem.as_uri() + '?mode=ro', uri=True)) as fonte:
        with closing(sqlite3.connect(destino)) as copia:
            fonte.backup(copia)
            if copia.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Backup reprovado na verificação de integridade.')
    return destino


def registrar_comandos(app):
    @app.cli.command('criar-admin')
    @click.option('--email', prompt=True)
    @click.option('--nome', prompt=True)
    @click.password_option()
    @with_appcontext
    def criar_admin(email, nome, password):
        """Cria o primeiro administrador sem abrir cadastro público."""
        email = email.strip().lower()
        if not validar_email(email) or len(nome.strip()) < 2 or len(password) < 12:
            raise click.ClickException('Informe email válido, nome e senha com pelo menos 12 caracteres.')
        if Participante.query.filter_by(email=email).first():
            raise click.ClickException('Email já existe; nenhuma conta foi alterada.')
        db.session.add(Participante(nome=nome.strip(), email=email, senha=hash_senha(password),
                                   admin=True, admin_global=True, conta_ativa=True))
        db.session.commit()
        click.echo('Administrador criado.')

    @app.cli.command('backup-banco')
    @click.argument('destino', type=click.Path())
    @with_appcontext
    def backup_banco(destino):
        """Cria cópia consistente SQLite, inclusive com o sistema em uso."""
        if db.engine.url.get_backend_name() != 'sqlite':
            raise click.ClickException('Este comando requer SQLite.')
        try:
            backup_sqlite(db.engine.url.database, destino)
        except (OSError, sqlite3.Error, ValueError):
            raise click.ClickException('Backup falhou. Verifique destino, espaço e permissões; o arquivo não deve existir.') from None
        click.echo('Backup criado e integridade verificada.')
