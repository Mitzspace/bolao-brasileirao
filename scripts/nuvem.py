"""Executa administração remota com arquivo privado, sem alterar o .env local."""
import argparse
from pathlib import Path

from dotenv import dotenv_values


def main():
    import os
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=Path('.env.neon.local'))
    parser.add_argument('acao', choices=['inicializar', 'criar-admin', 'verificar-limiter'])
    args = parser.parse_args()
    if not args.env_file.is_file():
        parser.error('Arquivo privado de configuração não encontrado.')
    valores = dotenv_values(args.env_file)
    if not valores.get('DATABASE_URL') or not valores.get('SECRET_KEY'):
        parser.error('Preencha DATABASE_URL e SECRET_KEY no arquivo privado.')
    os.environ.update({k: v for k, v in valores.items() if v is not None})
    os.environ['APP_ENV'] = 'production'
    os.environ['RATELIMIT_STORAGE_URI'] = 'memory://'
    os.environ['RATELIMIT_SINGLE_PROCESS'] = 'true'
    from config import normalizar_database_url
    from sqlalchemy.engine import make_url
    if make_url(normalizar_database_url(os.environ['DATABASE_URL'])).get_backend_name() != 'postgresql':
        parser.error('Este comando requer PostgreSQL; SQLite local não será modificado.')
    from app import create_app
    if args.acao == 'inicializar':
        create_app(initialize_database=True)
        print('Schema inicializado/validado; nenhum registro foi apagado.')
    else:
        from flask.cli import FlaskGroup
        cli = FlaskGroup(create_app=create_app)
        cli.main(args=[args.acao], prog_name='nuvem')


if __name__ == '__main__':
    main()
