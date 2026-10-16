"""Compressão e cache do navegador (services/http_desempenho)."""
import gzip
import json

from tests.test_interface import entrar, gestao  # noqa: F401


def test_json_da_api_sai_comprimido_e_igual(client, gestao):
    usuario, boloes = gestao
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': boloes[0].id})
    normal = client.get('/interface/api/participantes')
    gz = client.get('/interface/api/participantes', headers={'Accept-Encoding': 'gzip, br'})
    assert normal.status_code == gz.status_code == 200
    assert 'Content-Encoding' not in normal.headers
    if len(normal.data) >= 1024:
        assert gz.headers['Content-Encoding'] == 'gzip'
        assert json.loads(gzip.decompress(gz.data)) == normal.get_json()
    assert 'Accept-Encoding' in gz.headers.get('Vary', '')


def test_arquivos_da_interface_ficam_no_navegador_e_comprimidos(client, app):
    from pathlib import Path
    pasta = Path(app.static_folder) / 'interface' / 'assets'
    arquivos = sorted(pasta.glob('*.js')) if pasta.is_dir() else []
    if not arquivos:
        import pytest
        pytest.skip('Interface não compilada neste ambiente.')
    url = '/static/interface/assets/' + arquivos[0].name
    r = client.get(url, headers={'Accept-Encoding': 'gzip'})
    assert r.status_code == 200
    assert 'immutable' in r.headers['Cache-Control'] and 'max-age=31536000' in r.headers['Cache-Control']
    assert r.headers['Content-Encoding'] == 'gzip'
    assert gzip.decompress(r.data) == arquivos[0].read_bytes()
    # Segunda leitura usa a versão já comprimida em memória e devolve o mesmo conteúdo.
    assert client.get(url, headers={'Accept-Encoding': 'gzip'}).data == r.data
    # Revalidação continua funcionando (304 sem corpo).
    etag = r.headers.get('ETag')
    if etag:
        assert client.get(url, headers={'If-None-Match': etag}).status_code == 304


def test_escudos_ficam_em_cache_e_nao_sao_recomprimidos(client, app):
    from pathlib import Path
    escudos = sorted((Path(app.static_folder) / 'escudos').glob('*.png'))
    if not escudos:
        import pytest
        pytest.skip('Sem escudos locais.')
    r = client.get('/static/escudos/' + escudos[0].name, headers={'Accept-Encoding': 'gzip'})
    assert r.status_code == 200 and 'max-age=604800' in r.headers['Cache-Control']
    assert 'Content-Encoding' not in r.headers  # PNG já é comprimido
