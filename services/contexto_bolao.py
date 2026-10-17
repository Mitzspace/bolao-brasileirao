"""Seleção e autorização do bolão sem confundir campeonato com bolão."""
import re
from functools import lru_cache
from flask import abort, current_app, g, request, session
from flask_login import current_user
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.orm import joinedload, selectinload
from models import Bolao, Jogo, Palpite, PalpiteLog, Participacao, Rodada

# Último bolão escolhido: cookie assinado de longa duração (sobrevive a fechar o navegador e
# a sair e entrar de novo). Guarda só os ids da conta e do bolão; a permissão é sempre conferida.
COOKIE_ULTIMO_BOLAO = 'ultimo_bolao'
DURACAO_ULTIMO_BOLAO = 400 * 24 * 3600


def ordem_rodada(rodada):
    return _ordem_rodada(rodada.nome, rodada.id)


@lru_cache(maxsize=4096)
def _ordem_rodada(nome, id):
    numeros = re.findall(r'\d+', nome)
    return (int(numeros[0]) if numeros else float('inf'), nome.casefold(), id)


def opcoes_rodadas(campeonato_id):
    # Jogos e resultados vêm junto (2 consultas no total), em vez de 1 consulta por
    # rodada e outra por jogo ao calcular o estado das 38 rodadas.
    rodadas = sorted(Rodada.query.filter_by(campeonato_id=campeonato_id)
                     .options(selectinload(Rodada.jogos).joinedload(Jogo.resultado)).all(), key=ordem_rodada)
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
    g.ultimo_bolao_para_cookie = bolao_id


def _serializador():
    return URLSafeSerializer(current_app.secret_key, salt='ultimo-bolao')


def _bolao_do_cookie():
    """Id do último bolão salvo no cookie desta conta (ou None se ausente, adulterado ou de outra conta)."""
    valor = request.cookies.get(COOKIE_ULTIMO_BOLAO)
    if not valor:
        return None
    try:
        dados = _serializador().loads(valor)
    except BadSignature:
        return None
    if not isinstance(dados, dict) or dados.get('u') != current_user.id:
        return None
    return dados.get('b')


def _bolao_da_ultima_atividade():
    """Em outro aparelho (sem cookie): o bolão em que a conta lançou palpite por último."""
    linha = (Participacao.query.with_entities(Participacao.bolao_id)
             .join(Palpite, Palpite.participacao_id == Participacao.id)
             .join(PalpiteLog, PalpiteLog.palpite_id == Palpite.id)
             .filter(PalpiteLog.alterado_por == current_user.id)
             .order_by(PalpiteLog.id.desc()).first())
    return linha[0] if linha else None


def gravar_cookie_ultimo_bolao(resposta):
    """after_request: grava o cookie só quando o bolão lembrado mudou (sem Set-Cookie a cada resposta)."""
    bolao_id = getattr(g, 'ultimo_bolao_para_cookie', None)
    if bolao_id is None or not current_user.is_authenticated or _bolao_do_cookie() == bolao_id:
        return resposta
    resposta.set_cookie(COOKIE_ULTIMO_BOLAO, _serializador().dumps({'u': current_user.id, 'b': bolao_id}),
                        max_age=DURACAO_ULTIMO_BOLAO, httponly=True, samesite='Lax',
                        secure=bool(current_app.config.get('SESSION_COOKIE_SECURE')))
    return resposta


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
    disponiveis = {b.id for b in g.boloes_disponiveis}
    if escolhido not in disponiveis and len(disponiveis) > 1:
        # Sessão nova (outro navegador, login lembrado, sessão expirada): volta ao último bolão escolhido.
        escolhido = _bolao_do_cookie()
        if escolhido not in disponiveis:
            escolhido = _bolao_da_ultima_atividade()
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
