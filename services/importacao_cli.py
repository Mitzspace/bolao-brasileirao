"""Entrada compartilhada dos importadores antigos, sem exclusão de histórico."""
import argparse
from pathlib import Path

from app import create_app
from database import db
from models import Bolao, Campeonato, Participacao, Participante
from services.importador_planilha import importar_planilha_bolao


def importar(caminho, admin_email, nome, ano, *, importar_bonus=False):
    caminho = Path(caminho).expanduser().resolve()
    if not caminho.is_file() or caminho.suffix.lower() != '.xlsx':
        raise ValueError('Informe uma planilha .xlsx existente.')
    from services.validacao_formularios import texto, inteiro
    nome = texto(nome, 'Campeonato')
    ano = inteiro(ano, 'Temporada', 1, 9999)
    admin = Participante.query.filter_by(email=admin_email.strip().lower(), conta_ativa=True).first()
    if not admin or not admin.admin_global:
        raise ValueError('Informe o e-mail de um administrador global ativo.')
    if Campeonato.query.filter_by(nome=nome, ano=ano).first():
        raise ValueError('Este campeonato e temporada já existem. Use a importação da interface para atualizar.')
    try:
        campeonato = Campeonato(nome=nome, ano=ano)
        bolao = Bolao(nome=nome, campeonato=campeonato, criador=admin)
        db.session.add(Participacao(bolao=bolao, usuario=admin, participante_legado_id=admin.id,
                                   nome_exibicao=admin.nome, papel='responsavel'))
        db.session.flush()
        resultado = importar_planilha_bolao(caminho, campeonato.id, commit=False,
                                            importar_bonus=importar_bonus)
        db.session.commit()
        return resultado
    except Exception:
        db.session.rollback()
        raise


def main(*, importar_bonus=False):
    parser = argparse.ArgumentParser(description='Importa em um novo campeonato, preservando os existentes.')
    parser.add_argument('planilha', type=Path)
    parser.add_argument('--admin-email', required=True)
    parser.add_argument('--campeonato', required=True)
    parser.add_argument('--ano', required=True, type=int)
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        try:
            resultado = importar(args.planilha, args.admin_email, args.campeonato, args.ano,
                                 importar_bonus=importar_bonus)
        except ValueError as erro:
            parser.error(str(erro))
        print('Importação concluída:', resultado)
