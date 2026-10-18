"""Horários oficiais dos jogos (football-data.org) sob demanda, para a nova interface.

No Render Free o worker de sincronização fica desligado; por isso a interface pede
uma atualização ao abrir a aba Jogos. Aqui só são gravados horários: placares e
encerramento continuam seguindo o fluxo atual (manual ou tela de sincronização).

A API gratuita aceita poucas chamadas por minuto, então cada campeonato é
consultado no máximo uma vez a cada INTERVALO (o servidor usa um único processo).
"""
import os
import threading
from datetime import timedelta
from urllib.error import HTTPError, URLError

from flask import current_app

from database import db
from services.relogio import agora_brasilia
from services.sync import sync_informacoes_jogos

INTERVALO = timedelta(minutes=30)
INTERVALO_MANUAL = timedelta(minutes=2)
_trava = threading.Lock()
_tentativas = {}   # campeonato_id -> horário da última chamada à API
_sucessos = {}     # campeonato_id -> horário da última atualização bem-sucedida


def token_api():
    return current_app.config.get('FOOTBALL_DATA_TOKEN') or os.environ.get('FOOTBALL_DATA_TOKEN')


def ultima_atualizacao(campeonato_id):
    return _sucessos.get(campeonato_id)


def atualizar_horarios(campeonato, forcar=False):
    """Retorna um resumo; nunca lança erro de rede para quem chamou."""
    if campeonato.fonte_api == 'api-football':
        # Cota de 100 requisições/dia no plano gratuito: os horários vêm só da sincronização.
        return {'status': 'sem_codigo', 'mensagem': 'Campeonato da API-Football: os horários são atualizados '
                'pela sincronização do campeonato (Configurações › Campeonatos).'}
    token = token_api()
    if not token:
        return {'status': 'sem_token', 'mensagem': 'Configure FOOTBALL_DATA_TOKEN para buscar os horários oficiais.'}
    if not campeonato.codigo_api:
        return {'status': 'sem_codigo', 'mensagem': 'O campeonato não tem código da API configurado.'}
    agora = agora_brasilia()
    with _trava:
        ultima = _tentativas.get(campeonato.id)
        espera = INTERVALO_MANUAL if forcar else INTERVALO
        if ultima and agora - ultima < espera:
            return {'status': 'recente', 'horariosAtualizados': 0}
        _tentativas[campeonato.id] = agora
    try:
        resultado = sync_informacoes_jogos(
            token, campeonato.id, campeonato.codigo_api.strip().upper(),
            temporada=str(campeonato.ano) if campeonato.ano else None,
            salvar_resultados=False)
    except HTTPError as e:
        db.session.rollback()
        mensagem = ('Limite de consultas da API atingido; tente em alguns minutos.' if e.code == 429
                    else f'A API recusou a consulta ({e.code}). Verifique o token e o código do campeonato.')
        return {'status': 'erro', 'mensagem': mensagem}
    except (URLError, TimeoutError, OSError):
        db.session.rollback()
        return {'status': 'erro', 'mensagem': 'Não foi possível conectar à API de horários.'}
    _sucessos[campeonato.id] = agora
    return {'status': 'ok', 'horariosAtualizados': resultado['horarios_atualizados'],
            'jogosCasados': resultado['atualizados'], 'ignorados': resultado['ignorados']}
