"""Worker periódico: python -m services.sync_automatico (um processo por instalação)."""
import logging
import os
import time

from database import db
from models import Campeonato
from services.sync import sync_informacoes_jogos

logger = logging.getLogger(__name__)


def sincronizar_ciclo(app):
    token = app.config.get("FOOTBALL_DATA_TOKEN")
    if not token:
        raise ValueError("Configure FOOTBALL_DATA_TOKEN para a sincronização automática.")
    with app.app_context():
        campeonatos = [(c.id, c.codigo_api, c.ano) for c in Campeonato.query.all()
                       if c.codigo_api and c.rodadas]
        for id, codigo, ano in campeonatos:
            try:
                resultado = sync_informacoes_jogos(token, id, codigo, temporada=ano)
                logger.info("Campeonato %s sincronizado: %s", id, resultado)
            except Exception:
                db.session.rollback()
                logger.exception("Falha ao sincronizar campeonato %s; nova tentativa no próximo ciclo", id)


def main():
    from app import create_app
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    intervalo = max(60, int(os.environ.get("SYNC_INTERVALO_SEGUNDOS", "900")))
    if not app.config.get("FOOTBALL_DATA_TOKEN"):
        raise SystemExit("Configure FOOTBALL_DATA_TOKEN antes de iniciar o worker.")
    while True:
        try:
            sincronizar_ciclo(app)
        except Exception:
            logger.exception("Ciclo de sincronização falhou; será repetido")
        time.sleep(intervalo)


if __name__ == "__main__":
    main()
