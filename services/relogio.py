"""Datas de partidas legadas são horário de Brasília sem offset no banco."""
from datetime import datetime
from zoneinfo import ZoneInfo


def agora_brasilia():
    return datetime.now(ZoneInfo('America/Sao_Paulo')).replace(tzinfo=None)
