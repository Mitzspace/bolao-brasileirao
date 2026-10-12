"""Seleção e autorização do bolão sem confundir campeonato com bolão."""
import re
from flask import abort, current_app, g, redirect, request, session, url_for
from flask_login import current_user
from sqlalchemy.orm import joinedload
from models import Bolao, Campeonato, Participacao, Rodada


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
        Participacao.usuario_id == current_user.id, Participacao.status == 'ativo')
    if not current_app.config['FEATURE_PARTICIPANTE_LOGIN']:
        query = query.filter(Participacao.papel == 'responsavel')
    return (query
            .options(joinedload(Bolao.campeonato), joinedload(Bolao.criador))
            .order_by(Bolao.nome, Bolao.id).all())


def lembrar_bolao(bolao_id):
    session['bolao_id'] = bolao_id
    session['bolao_usuario_id'] = current_user.id
    session['ultimo_bolao'] = {'usuario_id': current_user.id, 'bolao_id': bolao_id}


def rota_depende_de_bolao(endpoint=None):
    endpoint = endpoint or request.endpoint or ''
    return (endpoint.startswith('admin.') or (
        endpoint.startswith('participante.') and endpoint not in {
            'participante.escolher_bolao', 'participante.selecionar_bolao', 'participante.criar_bolao'}))


def carregar_contexto():
    g.boloes_disponiveis = boloes_permitidos()
    g.bolao_atual = None
    g.participacao_atual = None
    depende = rota_depende_de_bolao()
    if not current_user.is_authenticated:
        session.pop('bolao_id', None)
        session.pop('bolao_usuario_id', None)
        if depende:
            return redirect(url_for('auth.login'))
        return

    escolhido = (session.get('bolao_id')
                 if session.get('bolao_usuario_id') == current_user.id else None)
    ultimo = session.get('ultimo_bolao', {})
    if escolhido is None and ultimo.get('usuario_id') == current_user.id:
        escolhido = ultimo.get('bolao_id')
    caminho = getattr(g, 'bolao_path_id', None)
    explicito = depende and (caminho is not None or 'bolao_id' in request.args)
    if depende and 'bolao_id' in request.args:
        valores = request.args.getlist('bolao_id')
        escolhido = request.args.get('bolao_id', type=int)
        if len(valores) != 1 or escolhido is None:
            abort(403)
        if caminho is not None and escolhido != caminho:
            abort(403)
    if caminho is not None:
        escolhido = caminho
    g.bolao_atual = next((b for b in g.boloes_disponiveis if b.id == escolhido), None)
    if explicito and g.bolao_atual is None:
        abort(403)
    if g.bolao_atual is None and len(g.boloes_disponiveis) == 1:
        g.bolao_atual = g.boloes_disponiveis[0]
    if g.bolao_atual:
        g.participacao_atual = Participacao.query.filter_by(
            bolao_id=g.bolao_atual.id, usuario_id=current_user.id, status='ativo').first()
        if g.participacao_atual is None:
            g.bolao_atual = None
    if g.bolao_atual:
        if (depende and request.method == 'POST' and 'bolao_id' in request.form
                and (len(request.form.getlist('bolao_id')) != 1
                     or request.form.get('bolao_id', type=int) != g.bolao_atual.id)):
            abort(403)
        lembrar_bolao(g.bolao_atual.id)
    else:
        session.pop('bolao_id', None)
        session.pop('bolao_usuario_id', None)
        if ultimo.get('usuario_id') == current_user.id:
            session.pop('ultimo_bolao', None)
        if depende:
            return redirect(url_for('participante.escolher_bolao'))


def bolao_atual():
    return getattr(g, 'bolao_atual', None)


def campeonatos_do_contexto():
    bolao = bolao_atual()
    if bolao:
        return [bolao.campeonato]
    if Bolao.query.first():
        return []
    return Campeonato.query.order_by(Campeonato.ano.desc()).all()


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


def contexto_templates():
    """Compartilha o contexto já validado, sem consultas durante a renderização."""
    return {'bolao_atual': bolao_atual(),
            'boloes_disponiveis': getattr(g, 'boloes_disponiveis', []),
            'participacao_atual': minha_participacao(),
            'responsavel_bolao': responsavel_atual()}


def contexto_nas_urls(endpoint, values):
    """Mantém links, ações e redirecionamentos no bolão desta requisição."""
    bolao = bolao_atual()
    if rota_depende_de_bolao(endpoint):
        if bolao:
            values.setdefault('bolao_id', bolao.id)
        if not current_app.config['FEATURE_PARTICIPANTE_LOGIN'] and 'bolao_id' in values:
            values['bolao_path_id'] = values.pop('bolao_id')


def destino_troca_bolao(bolao, formulario):
    """Resolve somente destinos conhecidos, sem confiar em URLs do formulário."""
    inicio = url_for('participante.inicio', bolao_id=bolao.id)
    origem = next((b for b in g.boloes_disponiveis
                   if b.id == formulario.get('bolao_origem_id', type=int)), None)
    if origem is None:
        return inicio
    aba = formulario.get('aba_origem')
    if (not current_app.config['FEATURE_PARTICIPANTE_LOGIN'] and aba in {
            'participante.meus_palpites', 'participante.visualizar_rodada'}):
        return url_for('admin.gerenciar_palpites', bolao_id=bolao.id)
    valores = {'bolao_id': bolao.id}
    if aba == 'participante.ranking' and origem.campeonato_id == bolao.campeonato_id:
        rodada_id = formulario.get('rodada_origem_id', type=int)
        if rodada_id and Rodada.query.filter_by(id=rodada_id, campeonato_id=bolao.campeonato_id).first():
            valores['rodada_id'] = rodada_id
    if aba == 'participante.meus_palpites' and origem.campeonato_id == bolao.campeonato_id:
        chave = formulario.get('rodada_origem')
        if chave in {chave for _, chave in opcoes_rodadas(bolao.campeonato_id)}:
            valores['rodada'] = chave
    if aba in {'participante.inicio', 'participante.meus_palpites',
               'participante.ranking', 'participante.tabela'}:
        return url_for(aba, **valores)
    if aba in {'participante.listar_jogos', 'participante.visualizar_rodada',
               'participante.ver_grade_palpites'}:
        rodada_id = formulario.get('rodada_origem_id', type=int)
        rodada = (Rodada.query.filter_by(id=rodada_id, campeonato_id=bolao.campeonato_id).first()
                  if rodada_id and origem.campeonato_id == bolao.campeonato_id else None)
        if (rodada is None and not current_app.config['FEATURE_PARTICIPANTE_LOGIN']
                and aba == 'participante.ver_grade_palpites'):
            from services.resumo_boloes import rodadas_de_referencia
            rodada = rodadas_de_referencia({bolao.campeonato_id})[bolao.campeonato_id]['rodada']
        if rodada:
            valores['rodada_id' if aba == 'participante.listar_jogos' else 'id'] = rodada.id
            if aba == 'participante.visualizar_rodada' and not rodada.aberta:
                return inicio
        elif aba != 'participante.listar_jogos':
            return inicio
        return url_for(aba, **valores)
    administrativas = {'admin.dashboard', 'admin.gerenciar_palpites', 'admin.responsaveis',
        'admin.listar_participantes', 'admin.listar_campeonatos',
        'admin.cadastrar_campeonato', 'admin.cadastrar_rodada', 'admin.cadastrar_jogo',
        'admin.cadastrar_resultados', 'admin.importar_jogos', 'admin.importar_resultados',
        'admin.sync', 'admin.importar_planilha'}
    if aba in administrativas:
        part = Participacao.query.filter_by(bolao_id=bolao.id,
            usuario_id=current_user.id, status='ativo').first()
        if part and (current_user.admin_global or part.papel == 'responsavel'):
            if not current_app.config['FEATURE_PARTICIPANTE_LOGIN']:
                from services.permissoes import ROTAS_GLOBAIS
                if aba.removeprefix('admin.') in ROTAS_GLOBAIS and not current_user.admin_global:
                    return inicio
                if origem.campeonato_id == bolao.campeonato_id and aba in {
                        'admin.gerenciar_palpites', 'admin.cadastrar_resultados'}:
                    rodada_id = formulario.get('rodada_origem_id', type=int)
                    if Rodada.query.filter_by(id=rodada_id, campeonato_id=bolao.campeonato_id).first():
                        valores['rodada_id'] = rodada_id
                return url_for(aba, **valores)
            if (current_user.admin_global or aba in {'admin.dashboard', 'admin.gerenciar_palpites'}
                    or Bolao.query.count() == 1):
                # Filtros de pessoa/jogo antigos não são transferidos entre bolões.
                return url_for(aba, **valores)
    return inicio
