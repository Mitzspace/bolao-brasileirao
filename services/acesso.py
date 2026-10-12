"""Desativação reversível do acesso de participantes, sem alterar contas."""
from flask import abort, current_app, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException, MethodNotAllowed
from models import Participacao


ROTAS_PARTICIPANTE = {
    "auth.cadastro", "participante.meus_palpites",
    "participante.visualizar_rodada",
}


def pode_acessar_gestao(usuario):
    return bool(usuario.admin_global or Participacao.query.filter_by(
        usuario_id=usuario.id, papel="responsavel", status="ativo"
    ).first())


def restringir_acesso_participante():
    if current_app.config["FEATURE_PARTICIPANTE_LOGIN"]:
        return
    endpoint = request.endpoint
    if isinstance(request.routing_exception, MethodNotAllowed):
        try:
            endpoint, _ = current_app.url_map.bind_to_environ(request.environ).match(method='GET')
        except HTTPException:
            pass
    if endpoint in ROTAS_PARTICIPANTE:
        abort(404)
    # Verifica também sessões abertas antes da desativação ou da remoção do papel.
    if (current_user.is_authenticated
            and request.blueprint in {"auth", "admin", "participante"}
            and request.endpoint != "auth.logout"
            and not pode_acessar_gestao(current_user)):
        abort(403)
