"""Escopo dos registros administrativos no modo de gestão."""
from flask import abort, request
from flask_login import current_user
from models import Campeonato, Jogo, Participacao, Rodada
from services.contexto_bolao import bolao_atual, validar_rodada


ROTAS_GLOBAIS = {
    'sync', 'importar_jogos', 'importar_resultados', 'importar_planilha',
    'cadastrar_campeonato', 'editar_participante', 'toggle_admin', 'cadastrar_participante',
}


def validar_escopo_admin(nome, argumentos):
    bolao = bolao_atual()
    if not bolao:
        abort(403)
    if nome in ROTAS_GLOBAIS and not current_user.admin_global:
        abort(403)
    id = argumentos.get('id')
    if id is not None:
        if nome in {'editar_jogo', 'encerrar_jogo', 'reabrir_jogo', 'excluir_jogo'}:
            validar_rodada(Jogo.query.get_or_404(id).rodada)
        elif nome in {'toggle_rodada', 'excluir_rodada'}:
            validar_rodada(Rodada.query.get_or_404(id))
        elif nome in {'editar_campeonato', 'excluir_campeonato'}:
            if id != bolao.campeonato_id:
                abort(404)
        elif nome in {'editar_participante', 'toggle_admin', 'excluir_participante'}:
            Participacao.query.filter_by(bolao_id=bolao.id, participante_legado_id=id).first_or_404()
    for valores in (request.args, request.form):
        for campo in ('campeonato_id', 'rodada_id', 'jogo_id'):
            if campo not in valores or valores.get(campo) == '':
                continue
            valor = valores.get(campo, type=int)
            if valor is None or len(valores.getlist(campo)) != 1:
                abort(400)
            if campo == 'campeonato_id' and valor != bolao.campeonato_id:
                abort(404)
            if campo == 'rodada_id':
                validar_rodada(Rodada.query.get_or_404(valor))
            if campo == 'jogo_id':
                validar_rodada(Jogo.query.get_or_404(valor).rodada)
