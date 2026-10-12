"""Mantém o serviço e o SSH disponíveis sem abrir o banco durante restauração."""
from flask import Flask

app = Flask(__name__)


@app.get('/healthz')
def health():
    return {'status': 'maintenance'}


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def maintenance(path):
    return 'Sistema em manutenção. Tente novamente em alguns minutos.', 503, {'Retry-After': '300'}
