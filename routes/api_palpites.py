"""Lançamento de palpites na nova interface (mesmo serviço da tela atual)."""
from flask import jsonify, request
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import MultiDict

from database import db
from models import Participacao, Rodada
from routes.api import api, erro, requer_gestao
from routes.api_serializacao import serializar_jogo
from services.contexto_bolao import bolao_atual, opcoes_rodadas, validar_rodada
from services.elegibilidade import participa_na_rodada
from services.estado_rodadas import estados_das_rodadas
from services.fluxo_lancamento import lembrar_rodada, proximo_pendente, rodada_padrao, vizinhos
from services.lancamento_palpites import (gerar_previa, palpites_existentes, participantes_do_lancamento,
                                          pessoa_do_lancamento, salvar_lote)
from services.pontuacao import calcular_pontuacao
from services.relogio import agora_brasilia
from services.resumo_boloes import participantes_pendentes


def _rodada(id):
    rodada = Rodada.query.get_or_404(id)
    validar_rodada(rodada)
    return rodada


@api.get('/palpites')
@requer_gestao()
def tela_palpites():
    bolao = bolao_atual()
    rodadas = [r for r, _ in opcoes_rodadas(bolao.campeonato_id)]
    if request.args.get('rodada_id'):
        rodada = _rodada(request.args.get('rodada_id', type=int))
    else:
        rodada = rodada_padrao(bolao, rodadas)
    if rodada is None:
        return jsonify({'rodadas': [], 'rodada': None, 'participantes': [], 'pessoa': None, 'jogos': []})
    lembrar_rodada(bolao, rodada)
    estados = estados_das_rodadas(bolao, rodadas)
    elegiveis = [p for p in participantes_do_lancamento(bolao) if participa_na_rodada(p, rodada)]
    faltantes = {item['participacao'].id: item['faltantes'] for item in participantes_pendentes(bolao, rodada)}

    pessoa = None
    if request.args.get('participacao_id'):
        pessoa = pessoa_do_lancamento(bolao, request.args.get('participacao_id', type=int), rodada)
    elif elegiveis:
        pessoa = next((p for p in elegiveis if p.id in faltantes), elegiveis[0])

    jogos = []
    if pessoa:
        existentes = palpites_existentes(bolao, pessoa, rodada.id)
        agora = agora_brasilia()
        for numero, jogo in enumerate(rodada.jogos, 1):  # mesma ordem usada pela leitura do WhatsApp
            p = existentes.get(jogo.id)
            resultado = jogo.resultado
            jogos.append({
                **serializar_jogo(jogo, bolao.campeonato_id),
                'numero': numero,
                'iniciado': bool(jogo.data and jogo.data <= agora),
                'palpite': {
                    'casa': p.gols_casa if p.situacao == 'valido' else None,
                    'fora': p.gols_fora if p.situacao == 'valido' else None,
                    'primeiroGol': p.primeiro_gol or '',
                    'situacao': p.situacao,
                    'guardado': bool(p.excluido_por_desistencia),
                    'pontos': (0 if p.excluido_por_desistencia else calcular_pontuacao(p, jogo, resultado).total)
                              if resultado else None,
                } if p else None,
            })
    anterior, proxima = vizinhos(elegiveis, pessoa.id if pessoa else None)
    return jsonify({
        'rodadas': [{'id': r.id, 'numero': i, 'nome': r.nome, **estados[r.id]} for i, r in enumerate(rodadas, 1)],
        'rodada': {'id': rodada.id, 'nome': rodada.nome, **estados[rodada.id]},
        'participantes': [{'id': p.id, 'nome': p.nome, 'status': p.status, 'faltantes': faltantes.get(p.id, 0)}
                          for p in elegiveis],
        'pessoa': {'id': pessoa.id, 'nome': pessoa.nome, 'status': pessoa.status,
                   'anteriorId': anterior, 'proximaId': proxima} if pessoa else None,
        'jogos': jogos,
    })


def _formulario(corpo):
    """Converte o JSON da tela nova nos mesmos campos do formulário atual."""
    campos = MultiDict()
    for nome, chave in (('recebido_em', 'recebidoEm'), ('whatsapp_token', 'whatsappToken'),
                        ('whatsapp_jogos', 'whatsappJogos')):
        if corpo.get(chave):
            campos[nome] = str(corpo[chave])
    if corpo.get('naoEnviouRodada'):
        campos['nao_enviou_rodada'] = '1'
    for jogo_id, valores in (corpo.get('jogos') or {}).items():
        if not str(jogo_id).isdecimal() or not isinstance(valores, dict):
            continue
        for campo, chave in (('casa', 'casa'), ('fora', 'fora'), ('primeiro', 'primeiroGol'), ('situacao', 'situacao')):
            if chave in valores and valores[chave] is not None:
                campos[f'{campo}_{jogo_id}'] = str(valores[chave])
    return campos


@api.post('/palpites')
@requer_gestao()
def salvar_palpites():
    from services.responsaveis import bloquear_bolao
    bolao = bolao_atual()
    corpo = request.get_json(silent=True) or {}
    acao = corpo.get('acao', 'ficar')
    if acao not in {'ficar', 'proximo'}:
        return erro(400, 'Ação de salvamento inválida.')
    try:
        rodada_id, pessoa_id = int(corpo.get('rodadaId')), int(corpo.get('participacaoId'))
    except (TypeError, ValueError):
        return erro(400, 'Selecione uma pessoa e uma rodada.')
    bloquear_bolao(bolao.id)
    rodada = _rodada(rodada_id)
    pessoa = pessoa_do_lancamento(bolao, pessoa_id, rodada)
    try:
        quantidade, erros = salvar_lote(bolao, pessoa, rodada, _formulario(corpo), current_user.id)
    except IntegrityError:
        # O banco aceita um único palpite por pessoa e jogo. Se dois envios chegarem
        # juntos, o segundo é recusado aqui em vez de virar erro 500.
        db.session.rollback()
        return erro(409, 'Estes palpites acabaram de ser gravados por outro envio. '
                         'Confira a tela antes de salvar de novo.')
    if erros:
        return erro(422, 'Nada foi salvo. Corrija os campos indicados e salve novamente.',
                    erros={str(k): v for k, v in erros.items()})
    lembrar_rodada(bolao, rodada)
    avisos, proximo_id = [], None
    if acao == 'proximo':
        proximo = proximo_pendente(bolao, rodada, pessoa.id, participantes_do_lancamento(bolao))
        if proximo is None:
            avisos.append('Todos os participantes elegíveis estão completos nesta rodada.')
        elif proximo == pessoa.id:
            avisos.append('Só este participante ainda tem pendências. Complete os jogos restantes ou revise os palpites guardados.')
        else:
            proximo_id = proximo
    return jsonify({'mensagem': f"{quantidade} palpites de '{pessoa.nome}' para a '{rodada.nome}' salvos com sucesso!",
                    'avisos': avisos, 'proximoId': proximo_id})


@api.post('/palpites/previa-whatsapp')
@requer_gestao()
def previa_whatsapp_api():
    bolao = bolao_atual()
    corpo = request.get_json(silent=True) or {}
    pessoa = Participacao.query.filter_by(id=corpo.get('participacaoId'), bolao_id=bolao.id).first_or_404()
    rodada = _rodada(corpo.get('rodadaId'))
    dados, status = gerar_previa(bolao, pessoa, rodada, str(corpo.get('texto') or ''), current_user.id)
    return jsonify(dados), status
