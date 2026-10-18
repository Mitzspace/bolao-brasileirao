"""Criação de bolão (tela atual e nova interface usam exatamente as mesmas regras)."""
from database import db
from models import Bolao, Campeonato, Participacao
from services.competicoes import (CODIGOS_PLANO_PAGO, FONTE_API_FOOTBALL, FONTE_FOOTBALL_DATA, FONTES_API,
                                  MODELOS_COMPETICAO)
from services.validacao_formularios import inteiro, texto

AVISO_FOOTBALL_DATA = ('A sincronização de Libertadores/Sul-Americana na football-data.org '
                       'exige token de plano pago.')
AVISO_API_FOOTBALL = ('A temporada atual na API-Football exige plano pago; o plano gratuito '
                      'só dá acesso às temporadas 2022 a 2024.')


def fonte_inferida(codigo_api):
    """Sem fonte informada: id numérico (ex.: 13) é liga da API-Football; códigos (BSA) são football-data."""
    return FONTE_API_FOOTBALL if (codigo_api or '').strip().isdigit() else FONTE_FOOTBALL_DATA


def aviso_plano_pago(codigo_api, fonte_api=None):
    fonte = fonte_api or fonte_inferida(codigo_api)
    if fonte == FONTE_API_FOOTBALL:
        return AVISO_API_FOOTBALL
    if (codigo_api or '').strip().upper() in CODIGOS_PLANO_PAGO:
        return AVISO_FOOTBALL_DATA
    return None


def modelos_disponiveis():
    return [{'chave': chave, **modelo, 'aviso': aviso_plano_pago(modelo['codigo_api'], modelo['fonte_api'])}
            for chave, modelo in MODELOS_COMPETICAO.items()]


def validar_fonte(fonte_api, codigo_api=None):
    """Fonte informada (ou inferida do código) validada; ValueError se desconhecida."""
    if fonte_api is None or fonte_api == '':
        return fonte_inferida(codigo_api)
    if not isinstance(fonte_api, str) or fonte_api not in FONTES_API:
        raise ValueError('Fonte da API inválida (use football-data ou api-football).')
    return fonte_api


def fontes_de_copia(usuario):
    """Bolões em que o usuário é responsável ativo: podem fornecer nomes de participantes."""
    return (Bolao.query.join(Participacao).filter(
        Participacao.usuario_id == usuario.id, Participacao.papel == 'responsavel',
        Participacao.status == 'ativo').order_by(Bolao.nome, Bolao.id).all())


def pessoas_da_origem(origem, usuario):
    """Participações que podem ser copiadas (o próprio responsável entra de qualquer forma)."""
    if origem is None:
        return []
    return (Participacao.query.filter(Participacao.bolao_id == origem.id,
            (Participacao.usuario_id.is_(None) | (Participacao.usuario_id != usuario.id)))
            .order_by(Participacao.nome_exibicao, Participacao.id).all())


def validar_dados(nome, campeonato_nome, campeonato_ano, codigo_api, modelo=None):
    """Devolve os valores normalizados ou levanta ValueError com a mensagem da tela atual."""
    if modelo is not None:
        if not isinstance(modelo, str) or modelo not in MODELOS_COMPETICAO:
            raise ValueError('Modelo de competição inválido.')
        padrao = MODELOS_COMPETICAO[modelo]
        campeonato_nome = (campeonato_nome or '').strip() or padrao['nome']
        codigo_api = (codigo_api or '').strip() or padrao['codigo_api']
    nome = (nome or '').strip()
    if not 2 <= len(nome) <= 100:
        raise ValueError('Informe um nome entre 2 e 100 caracteres.')
    campeonato_nome = texto(campeonato_nome, 'Campeonato')
    campeonato_ano = inteiro(campeonato_ano, 'Temporada', 1, 9999)
    codigo_api = texto(codigo_api or 'BSA', 'Código da API', 20).upper()
    return nome, campeonato_nome, campeonato_ano, codigo_api


def criar_bolao(usuario, nome, campeonato_nome, campeonato_ano, codigo_api, pessoas, selecionados,
                regras=None, eliminacao_participantes=False, fonte_api=None):
    """Cria bolão + campeonato próprio; o criador entra como responsável e os nomes marcados
    viram participantes ativos (sem conta, palpites ou pontos copiados). Faz commit.

    fonte_api: 'football-data' | 'api-football'; sem valor, é inferida do código (id numérico =
    API-Football), o que coincide com a fonte dos modelos de MODELOS_COMPETICAO."""
    if not isinstance(eliminacao_participantes, bool):
        raise ValueError('Eliminar participantes por fase deve ser um booleano.')
    fonte_api = validar_fonte(fonte_api, codigo_api)
    campeonato = Campeonato(nome=campeonato_nome, ano=campeonato_ano, codigo_api=codigo_api,
                            fonte_api=fonte_api)
    novo = Bolao(nome=nome, campeonato=campeonato, criador=usuario,
                 permite_palpite_proprio=False, permite_lancamento_por_responsavel=True,
                 eliminacao_participantes=eliminacao_participantes)
    if regras:
        from services.regras_pontuacao import aplicar_regras
        aplicar_regras(novo, regras)  # sem regras: valores padrão do modelo
    db.session.add(novo)
    db.session.add(Participacao(bolao=novo, usuario=usuario,
        nome_exibicao=usuario.nome, papel='responsavel', status='ativo'))
    for pessoa in pessoas:
        if pessoa.id in selecionados:
            db.session.add(Participacao(bolao=novo, nome_exibicao=pessoa.nome_exibicao,
                papel='participante', status='ativo'))
    db.session.commit()
    return novo


def mensagem_criacao(selecionados):
    return f'Bolão criado com {len(selecionados)} participantes copiados, além do responsável.'
