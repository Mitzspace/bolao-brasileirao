"""Worker periódico: python -m services.sync_automatico (um processo por instalação)."""
import logging
import os
import time

from database import db
from models import Campeonato
from services.competicoes import FONTE_API_FOOTBALL, FONTE_FOOTBALL_DATA, FONTES_API, normalizar_fonte
from services.sync import sync_competicao

logger = logging.getLogger(__name__)

# Variável de ambiente com a chave de cada provedor.
CHAVES = {FONTE_FOOTBALL_DATA: "FOOTBALL_DATA_TOKEN", FONTE_API_FOOTBALL: "API_FOOTBALL_KEY"}
# A API-Football gratuita tem 100 requisições/dia: cada (liga, ano) é consultado no máximo
# uma vez por API_FOOTBALL_INTERVALO_SEGUNDOS (padrão 1 h = 24 requisições/dia por liga).
_ultima_api_football = {}


def _intervalo_api_football():
    return max(60, int(os.environ.get("API_FOOTBALL_INTERVALO_SEGUNDOS", "3600")))


def _grupos():
    """(fonte, código, ano) distintos dos campeonatos com rodadas; uma chamada por grupo."""
    grupos = set()
    for c in Campeonato.query.all():
        if not (c.codigo_api and c.codigo_api.strip() and c.rodadas):
            continue
        fonte = normalizar_fonte(c.fonte_api)
        codigo = c.codigo_api.strip().upper() if fonte == FONTE_FOOTBALL_DATA else c.codigo_api.strip()
        grupos.add((fonte, codigo, c.ano))
    return sorted(grupos, key=lambda g: (g[0] != FONTE_FOOTBALL_DATA, g[0], g[1], g[2] or 0))


def sincronizar_ciclo(app, agora=None):
    chaves = {fonte: app.config.get(variavel) for fonte, variavel in CHAVES.items()}
    if not any(chaves.values()):
        raise ValueError("Configure FOOTBALL_DATA_TOKEN e/ou API_FOOTBALL_KEY para a sincronização automática.")
    agora = time.monotonic() if agora is None else agora
    with app.app_context():
        sem_chave = set()
        for fonte, codigo, ano in _grupos():
            chave = chaves.get(fonte)
            if not chave:
                if fonte not in sem_chave:
                    logger.warning("Sem %s: campeonatos da %s não serão sincronizados.",
                                   CHAVES[fonte], FONTES_API[fonte])
                    sem_chave.add(fonte)
                continue
            if fonte == FONTE_API_FOOTBALL:
                ultima = _ultima_api_football.get((codigo, ano))
                if ultima is not None and agora - ultima < _intervalo_api_football():
                    continue
                _ultima_api_football[(codigo, ano)] = agora
            try:
                if fonte == FONTE_FOOTBALL_DATA:
                    resultado = sync_competicao(chave, codigo, ano)
                else:
                    resultado = sync_competicao(chave, codigo, ano, fonte_api=fonte)
                logger.info("Competição %s %s/%s sincronizada: %s", FONTES_API[fonte], codigo, ano, resultado)
            except Exception:
                db.session.rollback()
                logger.exception("Falha ao sincronizar %s %s/%s; nova tentativa no próximo ciclo",
                                 FONTES_API[fonte], codigo, ano)


def main():
    from app import create_app
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    intervalo = max(60, int(os.environ.get("SYNC_INTERVALO_SEGUNDOS", "900")))
    if not (app.config.get("FOOTBALL_DATA_TOKEN") or app.config.get("API_FOOTBALL_KEY")):
        raise SystemExit("Configure FOOTBALL_DATA_TOKEN e/ou API_FOOTBALL_KEY antes de iniciar o worker.")
    while True:
        try:
            sincronizar_ciclo(app)
        except Exception:
            logger.exception("Ciclo de sincronização falhou; será repetido")
        time.sleep(intervalo)


if __name__ == "__main__":
    main()
