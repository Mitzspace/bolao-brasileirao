"""Marca como clássico os jogos já cadastrados cujo confronto está em services/classicos.py.

Uso, na pasta do projeto (usa o banco configurado no .env, como o app):
    python -m scripts.marcar_classicos            # só mostra o que mudaria
    python -m scripts.marcar_classicos --aplicar  # grava

Só marca (nunca desmarca) e não mexe em resultados, palpites nem pontos gravados.
Os pontos de jogos já decididos passam a seguir a regra de clássico do bolão.
"""
import sys

from app import create_app
from database import db
from models import Jogo
from services.classicos import eh_classico


def main(aplicar):
    app = create_app()
    with app.app_context():
        pendentes = [j for j in Jogo.query.filter_by(classico=False).all() if eh_classico(j.time_casa, j.time_fora)]
        for j in sorted(pendentes, key=lambda j: (j.rodada.campeonato_id, j.rodada.nome, j.id)):
            print(f'campeonato {j.rodada.campeonato_id} · {j.rodada.nome}: {j.time_casa} x {j.time_fora}')
        print(f'\n{len(pendentes)} jogo(s) {"marcados" if aplicar else "seriam marcados"} como clássico.')
        if aplicar and pendentes:
            for j in pendentes:
                j.especial = True
            db.session.commit()
        elif not aplicar and pendentes:
            print('Rode de novo com --aplicar para gravar.')


if __name__ == '__main__':
    main('--aplicar' in sys.argv)
