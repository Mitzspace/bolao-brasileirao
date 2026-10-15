"""Seleção e autorização do bolão sem confundir campeonato com bolão."""
import re
from flask import abort, g, session
from flask_login import current_user
from sqlalchemy.orm import joinedload
from models import Bolao, Participacao, Rodada


def ordem_rodada(rodada):
    numeros = re.findall(r'\d+', rodada.nome)
    return (int(numeros[0]) if numeros else float('inf'), rodada.nome.casefold(), rodada.id)


def opcoes_rodadas(campeonato_id):
    rodadas = sorted(Rodada.query.filter_by(campeonato_id=campeonato_id).all(), key=ordem_rodada)
    numeros = [re.findall(r'\d+', r.nome) for r in rodadas]
    chaves = [str(int(n[0])) if n else None for n in numeros]
    return [(r, chave if chave and chaves.count(chave) == 1 else f'id-{r.id}')
            for r, chave in zip(rodadas, chaves)]


def boloes_permitidos():
    if not current_user.is_authenticated:
        return []
    query = Bolao.query.join(Participacao).filter(
        Participacao.usuario_id == current_user.id, Participacao.status == 'ativo',
        Participacao.papel == 'responsavel')
    return (query
            .options(joinedload(Bolao.campeonato), joinedload(Bolao.criador))
            .order_by(Bolao.nome, Bolao.id).all())


def lembrar_bolao(bolao_id):
    session['bolao_id'] = bolao_id
    session['bolao_usuario_id'] = current_user.id
    session['ultimo_bolao'] = {'usuario_id': current_user.id, 'bolao_id': bolao_id}


def carregar_contexto():
    """Carrega o bolão selecionado na sessão (só bolões em que a conta é responsável ativa)."""
    g.boloes_disponiveis = boloes_permitidos()
    g.bolao_atual = None
    g.participacao_atual = None
    if not current_user.is_authenticated:
        session.pop('bolao_id', None)
        session.pop('bolao_usuario_id', None)
        return

    escolhido = (session.get('bolao_id')
                 if session.get('bolao_usuario_id') == current_user.id else None)
    ultimo = session.get('ultimo_bolao', {})
    if escolhido is None and ultimo.get('usuario_id') == current_user.id:
        escolhido = ultimo.get('bolao_id')
    g.bolao_atual = next((b for b in g.boloes_disponiveis if b.id == escolhido), None)
    if g.bolao_atual is None and len(g.boloes_disponiveis) == 1:
        g.bolao_atual = g.boloes_disponiveis[0]
    if g.bolao_atual:
        g.participacao_atual = Participacao.query.filter_by(
            bolao_id=g.bolao_atual.id, usuario_id=current_user.id, status='ativo').first()
        if g.participacao_atual is None:
            g.bolao_atual = None
    if g.bolao_atual:
        lembrar_bolao(g.bolao_atual.id)
    else:
        session.pop('bolao_id', None)
        session.pop('bolao_usuario_id', None)
        if ultimo.get('usuario_id') == current_user.id:
            session.pop('ultimo_bolao', None)


def bolao_atual():
    return getattr(g, 'bolao_atual', None)


def validar_rodada(rodada):
    bolao = bolao_atual()
    if bolao and rodada.campeonato_id != bolao.campeonato_id:
        abort(404)
    if not bolao and Bolao.query.first():
        abort(403)


def minha_participacao():
    return getattr(g, 'participacao_atual', None)


def responsavel_atual():
    part = minha_participacao()
    return bool(current_user.is_authenticated and bolao_atual() and part
                and part.status == 'ativo' and (
                    current_user.admin_global or part.papel == 'responsavel'))
