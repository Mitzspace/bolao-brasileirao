"""Cache em memória das respostas da área pública.

A mesma página é aberta por muita gente; sem cache, cada acesso recalcularia a
classificação no processador pequeno do Render Free e acordaria o Neon.

- Cada resposta fica guardada por até TTL segundos.
- Qualquer gravação no banco feita por este processo (lançar palpite, resultado,
  liberar tabela, regenerar link...) muda a "versão dos dados" e invalida tudo na hora.
- O TTL cobre alterações feitas fora do app (SQL Editor do Neon, scripts).
O app roda com um único processo (gunicorn.conf.py), então o cache é consistente.
"""
import threading
import time

from sqlalchemy import event
from sqlalchemy.orm import Session

TTL = 60
LIMITE = 500

_versao = 0
_dados = {}
_trava = threading.Lock()


@event.listens_for(Session, 'before_flush')
def _marcar_alteracao(session, flush_context, instances):
    if session.new or session.dirty or session.deleted:
        session.info['_dados_alterados'] = True


@event.listens_for(Session, 'after_commit')
def _nova_versao(session):
    global _versao
    if session.info.pop('_dados_alterados', False):
        with _trava:
            _versao += 1
            _dados.clear()


@event.listens_for(Session, 'after_rollback')
def _descartar(session):
    session.info.pop('_dados_alterados', None)


def invalidar():
    """Esvazia o cache (usado pelos testes e por gravações fora do ORM)."""
    global _versao
    with _trava:
        _versao += 1
        _dados.clear()


def obter(chave, gerar):
    """Devolve o valor guardado para `chave` ou gera, guarda e devolve."""
    agora = time.monotonic()
    with _trava:
        item = _dados.get(chave)
        versao = _versao
    if item and item[0] == versao and item[1] > agora:
        return item[2]
    valor = gerar()
    with _trava:
        if versao == _versao:  # não guarda resultado calculado antes de uma gravação
            if len(_dados) >= LIMITE:
                _dados.clear()
            _dados[chave] = (versao, agora + TTL, valor)
    return valor
