"""Entrada compatível para importação; cria um campeonato e preserva o histórico.

Use --help para informar planilha, administrador, campeonato e temporada.
O nome legado não autoriza nem executa limpeza do banco.
"""
from services.importacao_cli import main


if __name__ == '__main__':
    main(importar_bonus=True)
