"""Mede, por tela, quantas consultas ao banco e quanto tempo de processamento a API gasta.

Trabalha numa CÓPIA temporária do banco SQLite (o original não é alterado) e entra
como o primeiro responsável ativo, sem precisar de senha.

Uso:
    python -m scripts.medir_desempenho instance/banco.db

Para comparar antes/depois, rode o mesmo comando no código antigo e no novo.
No Neon cada consulta é uma ida e volta pela rede (alguns milissegundos),
então "consultas" é o número que mais pesa em produção.
"""
import argparse
import os
import shutil
import tempfile
import time
from pathlib import Path


def medir(banco):
    from sqlalchemy import event
    os.environ.setdefault('APP_ENV', 'development')
    from app import create_app
    from database import db
    from models import Participacao, Rodada

    pasta = Path(tempfile.mkdtemp(prefix='medir-'))
    copia = pasta / 'banco.db'
    shutil.copy(banco, copia)
    try:
        from migrations.ordem_jogo import migrar
        migrar(copia)  # o código novo precisa da coluna jogo.ordem
    except ImportError:
        pass  # código antigo: não tem essa migração
    app = create_app('development', database_uri='sqlite:///' + copia.as_posix())
    app.config['RATELIMIT_ENABLED'] = False
    contador = {'n': 0}
    with app.app_context():
        event.listen(db.engine, 'before_cursor_execute',
                     lambda *a, **k: contador.__setitem__('n', contador['n'] + 1))
        resp = (Participacao.query.filter_by(papel='responsavel', status='ativo')
                .filter(Participacao.usuario_id.isnot(None)).first())
        if resp is None:
            raise SystemExit('Nenhum responsável ativo neste banco.')
        uid, bid = resp.usuario_id, resp.bolao_id
        rodadas = Rodada.query.filter_by(campeonato_id=resp.bolao.campeonato_id).all()
        rodada = rodadas[0].id if rodadas else None
    cliente = app.test_client()
    with cliente.session_transaction() as s:
        s['_user_id'] = str(uid)
        s['_fresh'] = True
        s['bolao_id'] = bid
        s['bolao_usuario_id'] = uid
    rotas = ['/interface/api/dashboard', '/interface/api/jogos', '/interface/api/palpites',
             '/interface/api/rodadas', '/interface/api/participantes', f'/interface/api/boloes/{bid}/classificacao',
             '/interface/api/campeonato']
    if rodada:
        rotas += [f'/interface/api/rodadas/{rodada}/classificacao', f'/interface/api/rodadas/{rodada}/grade']
    cliente.get('/interface/api/contexto')
    print(f'{"Tela (rota da API)":55} {"consultas":>9} {"tempo":>8} {"tamanho":>9}')
    for rota in rotas:
        contador['n'] = 0
        inicio = time.perf_counter()
        resposta = cliente.get(rota)
        ms = (time.perf_counter() - inicio) * 1000
        print(f'{rota:55} {contador["n"]:9} {ms:6.0f}ms {len(resposta.data) / 1024:7.1f}KB'
              + ('' if resposta.status_code == 200 else f'  (HTTP {resposta.status_code})'))
    shutil.rmtree(pasta, ignore_errors=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('banco', help='Arquivo SQLite (ex.: instance/banco.db)')
    medir(parser.parse_args().banco)
