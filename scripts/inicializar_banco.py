"""Cria schema vazio explicitamente; nunca apaga ou substitui dados existentes."""
from app import create_app

if __name__ == '__main__':
    create_app(initialize_database=True)
    print('Schema inicializado/validado. Nenhum registro foi apagado.')
