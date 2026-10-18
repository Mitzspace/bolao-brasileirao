"""Lançamento de palpites pelo responsável (lote por participante e rodada).

Extraído de routes/admin.py (gerenciar_palpites e previa_whatsapp) sem mudar
regras: validação integral antes de gravar (services/lancamento_lote), situação
do palpite, primeiro gol de clássico, texto do WhatsApp assinado e
auditoria automática (services/auditoria). Usado pela tela atual e pela API.
"""
import re

from flask import abort
from itsdangerous import BadSignature
from sqlalchemy.orm.attributes import flag_modified

from database import db
from models import Jogo, Palpite, Participacao, Participante
from services.elegibilidade import participa_na_rodada
from services.lancamento_lote import validar_lote
from services.relogio import agora_brasilia


def participantes_do_lancamento(bolao):
    if bolao:
        return (Participacao.query.filter(Participacao.bolao_id == bolao.id,
                Participacao.status.in_(['ativo', 'desistente']))
                .order_by(Participacao.nome_exibicao, Participacao.id).all())
    return Participante.query.order_by(Participante.nome).all()


def pessoa_do_lancamento(bolao, id, rodada=None):
    if bolao:
        pessoa = Participacao.query.filter(Participacao.id == id, Participacao.bolao_id == bolao.id,
            Participacao.status.in_(['ativo', 'desistente'])).populate_existing().first_or_404()
        if rodada and not participa_na_rodada(pessoa, rodada):
            abort(409, description='Esta pessoa não participa desta rodada. Confira entrada e desistência.')
        return pessoa
    return Participante.query.get_or_404(id)


def palpites_existentes(bolao, pessoa, rodada_id):
    return {p.jogo_id: p for p in Palpite.query.filter_by(
        **({'participacao_id': pessoa.id} if bolao else {'participante_id': pessoa.id})
    ).join(Jogo).filter(Jogo.rodada_id == rodada_id).all()}


def salvar_lote(bolao, pessoa, rodada, form, autor_id):
    """Grava o lote inteiro ou nada. Retorna (quantidade_salva, erros)."""
    existentes = palpites_existentes(bolao, pessoa, rodada.id)
    itens, erros = validar_lote(form, rodada.jogos, existentes)
    texto_original, jogos_texto = None, set()
    if form.get('whatsapp_token'):
        from services.texto_lancamento import ler_assinatura
        try:
            texto_original = ler_assinatura(form['whatsapp_token'], autor_id, bolao.id, pessoa.id, rodada.id)
            jogos_texto = {int(id) for id in form.get('whatsapp_jogos', '').split(',') if id}
            if not jogos_texto or not jogos_texto.issubset({j.id for j in rodada.jogos}):
                raise ValueError('Jogos inválidos.')
        except (BadSignature, ValueError, TypeError):
            erros['whatsapp'] = 'A prévia da mensagem expirou ou é inválida. Cole e revise a mensagem novamente.'
    if erros:
        db.session.rollback()
        return 0, erros
    for jogo, casa, fora, primeiro, (pen_casa, pen_fora) in itens:
        palpite = existentes.get(jogo.id)
        if palpite is None:
            palpite = Palpite(
                participante_id=pessoa.participante_legado_id if bolao else pessoa.id,
                participacao_id=pessoa.id if bolao else None, jogo_id=jogo.id)
            db.session.add(palpite)
        palpite.situacao = ('nao_enviado' if form.get('nao_enviou_rodada') == '1'
            else form.get(f'situacao_{jogo.id}', palpite.situacao or 'valido'))
        palpite.gols_casa = casa
        palpite.gols_fora = fora
        palpite.primeiro_gol = primeiro
        palpite.penaltis_casa, palpite.penaltis_fora = pen_casa, pen_fora
        palpite.origem = 'responsavel'
        # Origem registrada no log (services/auditoria): jogos preenchidos pela mensagem são "whatsapp".
        palpite._canal = 'whatsapp' if jogo.id in jogos_texto else 'painel'
        if jogo.id in jogos_texto:
            palpite._texto_original = texto_original
            if palpite.id:
                flag_modified(palpite, 'origem')
    db.session.commit()
    return len(itens), {}


def gerar_previa(bolao, pessoa, rodada, texto, autor_id):
    """Lê a mensagem do WhatsApp sem gravar nada. Retorna (dados, status_http)."""
    from services.parser_whatsapp import ler_mensagem, rodadas_informadas
    from services.texto_lancamento import assinatura
    if not participa_na_rodada(pessoa, rodada):
        abort(409, description='Esta pessoa não participa desta rodada.')
    if not texto.strip() or len(texto) > 20000 or len(texto.splitlines()) > 200:
        return {'erro': 'Cole uma mensagem com até 20.000 caracteres e 200 linhas.'}, 422
    cabecalhos = rodadas_informadas(texto)
    numeros = re.findall(r'\d+', rodada.nome)
    if cabecalhos and (len(numeros) != 1 or cabecalhos != {int(numeros[0])}):
        return {'erro': f'O cabeçalho informa rodada(s) {", ".join(map(str, sorted(cabecalhos)))}; a seleção é {rodada.nome}. Ajuste a rodada ou a mensagem antes de continuar.'}, 422
    jogos = list(rodada.jogos)
    existentes = {p.jogo_id: p for p in Palpite.query.filter_by(participacao_id=pessoa.id).join(Jogo).filter(Jogo.rodada_id == rodada.id)}
    linhas = ler_mensagem(texto, jogos)
    opcoes = []
    for jogo in jogos:
        avisos = []
        if jogo.id in existentes:
            avisos.append('Palpite existente: será sobrescrito ao salvar, com histórico.')
        bloqueado = jogo.id in existentes and existentes[jogo.id].excluido_por_desistencia
        if bloqueado:
            avisos.append('Após desistência: restaure no histórico antes de lançar.')
        if not rodada.aberta or jogo.encerrado or (jogo.data and jogo.data <= agora_brasilia()):
            avisos.append('Jogo iniciado ou fechado: lançamento permitido ao responsável e auditado.')
        opcoes.append({'id': jogo.id, 'nome': f'{jogo.time_casa} × {jogo.time_fora}', 'avisos': avisos,
                       'bloqueado': bloqueado, 'primeiro_gol_permitido': bool(jogo.especial),
                       'pode_penaltis': bool(jogo.pode_penaltis)})
    return {'linhas': linhas, 'jogos': opcoes, 'reconhecido': any(i['jogo_id'] is not None for i in linhas),
            'token': assinatura(texto, autor_id, bolao.id, pessoa.id, rodada.id)}, 200
