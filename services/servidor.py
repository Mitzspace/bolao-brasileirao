"""Supervisiona web e sincronização opcional (suspensa no Render Free ocioso)."""
import os
import signal
import subprocess
import sys
import time


def main():
    if os.environ.get('MAINTENANCE_MODE', 'false').lower() == 'true':
        os.execv(sys.executable, [sys.executable, '-m', 'gunicorn', '-c', 'gunicorn.conf.py', 'services.manutencao:app'])
    # Somente valida o schema. A inicialização de produção é sempre explícita.
    from app import create_app
    from database import db
    app = create_app()
    with app.app_context():
        db.engine.dispose()
    sincronizar = os.environ.get('SYNC_ENABLED', 'false').lower() == 'true'
    if sincronizar and not app.config.get('FOOTBALL_DATA_TOKEN'):
        raise SystemExit('SYNC_ENABLED requer FOOTBALL_DATA_TOKEN.')
    processos = []
    encerrando = False

    def parar(signum, frame):
        nonlocal encerrando
        encerrando = True

    signal.signal(signal.SIGTERM, parar)
    signal.signal(signal.SIGINT, parar)
    try:
        processos.append(subprocess.Popen([sys.executable, '-m', 'gunicorn', '-c', 'gunicorn.conf.py', 'wsgi:app']))
        if sincronizar:
            processos.append(subprocess.Popen([sys.executable, '-m', 'services.sync_automatico']))
        while not encerrando:
            if any(p.poll() is not None for p in processos):
                return 1  # Plataforma reinicia o conjunto se qualquer processo morrer.
            time.sleep(1)
        return 0
    finally:
        for p in processos:
            if p.poll() is None:
                p.terminate()
        limite = time.monotonic() + 35
        for p in processos:
            try:
                p.wait(timeout=max(0.1, limite - time.monotonic()))
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()


if __name__ == '__main__':
    sys.exit(main())
