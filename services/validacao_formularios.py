"""Conversões de formulário que falham antes de modificar o banco."""
import re
from datetime import datetime


def texto(valor, nome, limite=100):
    valor = (valor or '').strip()
    if not valor or len(valor) > limite:
        raise ValueError(f'{nome}: informe entre 1 e {limite} caracteres.')
    return valor


def inteiro(valor, nome, minimo=0, maximo=2147483647):
    valor = str(valor if valor is not None else '').strip()
    if not re.fullmatch(r'[0-9]{1,10}', valor):
        raise ValueError(f'{nome}: informe um número inteiro entre {minimo} e {maximo}.')
    numero = int(valor)
    if not minimo <= numero <= maximo:
        raise ValueError(f'{nome}: informe um número inteiro entre {minimo} e {maximo}.')
    return numero


def data_jogo(valor):
    if not valor or not valor.strip():
        return None
    try:
        return datetime.strptime(valor.strip(), '%Y-%m-%dT%H:%M')
    except ValueError:
        raise ValueError('Informe uma data e hora válidas para o jogo.') from None


def placar(casa, fora):
    return inteiro(casa, 'Gols da casa'), inteiro(fora, 'Gols de fora')
