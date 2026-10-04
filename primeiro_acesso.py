"""
primeiro_acesso.py — Configura o primeiro admin do bolão.

Execute UMA VEZ, logo após criar sua conta pelo /cadastro:

    python primeiro_acesso.py seu@email.com

Depois disso você pode promover outros participantes pela interface em /admin/participantes.
"""

import sys
from app import create_app
from database import db
from models import Participante
from werkzeug.security import generate_password_hash


def promover_admin(email):
    app = create_app()
    with app.app_context():
        p = Participante.query.filter_by(email=email).first()
        if p is None:
            print(f"ERRO: nenhum participante com email '{email}' encontrado.")
            print("Crie sua conta pelo /cadastro primeiro.")
            sys.exit(1)
        p.admin = True
        db.session.commit()
        print(f"Sucesso! '{p.nome}' agora é admin.")
        print("Acesse /admin no navegador para gerenciar o bolão.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python primeiro_acesso.py seu@email.com")
        sys.exit(1)
    promover_admin(sys.argv[1])
