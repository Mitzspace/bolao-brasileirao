"""Diagnóstico operacional sem imprimir URLs ou credenciais do armazenamento."""
import click
from flask import current_app
from flask.cli import with_appcontext
from urllib.parse import urlsplit

from extensions import limiter


@click.command('verificar-limiter')
@with_appcontext
def verificar_limiter():
    """Verifica se o backend compartilhado do rate limiter está acessível."""
    if not current_app.config.get('RATELIMIT_ENABLED', True):
        raise click.ClickException('O limiter está desativado neste ambiente.')
    if urlsplit(current_app.config['RATELIMIT_STORAGE_URI']).scheme == 'memory':
        if not current_app.config.get('RATELIMIT_SINGLE_PROCESS'):
            raise click.ClickException('Memória requer RATELIMIT_SINGLE_PROCESS=true e um único worker.')
        click.echo('Limiter local ativo; contadores reiniciam com o processo. Use apenas um worker.')
        return
    try:
        acessivel = limiter.storage.check()
    except Exception:
        # Exceções do driver podem conter a URL com a senha.
        raise click.ClickException('Não foi possível conectar ao armazenamento do limiter. Confira o serviço e as credenciais.') from None
    if not acessivel:
        raise click.ClickException('O armazenamento do limiter não respondeu à verificação.')
    click.echo('Armazenamento compartilhado do limiter acessível.')


def registrar_comando(app):
    app.cli.add_command(verificar_limiter)
