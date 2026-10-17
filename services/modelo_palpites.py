"""Modelo de palpites da rodada para colar no WhatsApp.

O formato é o que a leitura de mensagens (services/parser_whatsapp.py) já entende, para a
resposta do participante voltar sem avisos. Datas, prazo e instruções ficam de fora do
modelo de propósito: cada linha a mais viraria um aviso de "não reconhecido" ao colar a
resposta. O prazo sai separado, para ir como mensagem própria antes do modelo.
"""
import re
from datetime import datetime

from services.relogio import agora_brasilia

DIAS = ('seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom')


def numero_da_rodada(rodada):
    numeros = re.findall(r'\d+', rodada.nome)
    return int(numeros[0]) if len(numeros) == 1 else None


def jogo_iniciado(jogo, agora):
    """Já começou, foi encerrado à mão ou tem resultado: não entra no modelo."""
    return bool(jogo.encerrado or jogo.resultado is not None or (jogo.data is not None and jogo.data <= agora))


def texto_prazo(data):
    """Ex.: "Palpites até sáb 18/10, 16h" (com minutos quando houver: 16h30)."""
    hora = f'{data.hour}h' if data.minute == 0 else f'{data.hour}h{data.minute:02d}'
    return f'Palpites até {DIAS[data.weekday()]} {data:%d/%m}, {hora}'


def montar_modelo(rodada, agora=None):
    """Devolve texto, prazo (ou None), e quantos jogos entraram/ficaram de fora."""
    agora = agora or agora_brasilia()
    jogos = list(rodada.jogos)
    incluidos = [j for j in jogos if not jogo_iniciado(j, agora)]
    numero = numero_da_rodada(rodada)
    linhas = [f'*Rodada-{numero}*', ''] if numero is not None and incluidos else []
    linhas += [f'{j.time_casa} x {j.time_fora}' + (' ★' if j.classico else '') for j in incluidos]
    datas = [j.data for j in incluidos if isinstance(j.data, datetime)]
    return {
        'texto': '\n'.join(linhas),
        'prazo': texto_prazo(min(datas)) if datas else None,
        'incluidos': len(incluidos),
        'omitidos': len(jogos) - len(incluidos),
    }
