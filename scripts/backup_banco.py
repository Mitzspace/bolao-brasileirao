"""Backup independente da versão do schema: python -m scripts.backup_banco ORIGEM DESTINO."""
import argparse
from services.operacao import backup_sqlite

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origem')
    parser.add_argument('destino')
    args = parser.parse_args()
    backup_sqlite(args.origem, args.destino)
    print('Backup criado e verificado.')
