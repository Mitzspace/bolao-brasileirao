"""Quem pode entrar na gestão: administrador geral ou responsável ativo de algum bolão."""
from models import Participacao


def pode_acessar_gestao(usuario):
    return bool(usuario.admin_global or Participacao.query.filter_by(
        usuario_id=usuario.id, papel="responsavel", status="ativo"
    ).first())
