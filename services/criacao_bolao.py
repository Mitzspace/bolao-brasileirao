"""Criação de bolão (tela atual e nova interface usam exatamente as mesmas regras)."""
from database import db
from models import Bolao, Campeonato, Participacao
from services.validacao_formularios import inteiro, texto


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


def validar_dados(nome, campeonato_nome, campeonato_ano, codigo_api):
    """Devolve os valores normalizados ou levanta ValueError com a mensagem da tela atual."""
    nome = (nome or '').strip()
    if not 2 <= len(nome) <= 100:
        raise ValueError('Informe um nome entre 2 e 100 caracteres.')
    campeonato_nome = texto(campeonato_nome, 'Campeonato')
    campeonato_ano = inteiro(campeonato_ano, 'Temporada', 1, 9999)
    codigo_api = texto(codigo_api or 'BSA', 'Código da API', 20).upper()
    return nome, campeonato_nome, campeonato_ano, codigo_api


def criar_bolao(usuario, nome, campeonato_nome, campeonato_ano, codigo_api, pessoas, selecionados, regras=None):
    """Cria bolão + campeonato próprio; o criador entra como responsável e os nomes marcados
    viram participantes ativos (sem conta, palpites ou pontos copiados). Faz commit."""
    campeonato = Campeonato(nome=campeonato_nome, ano=campeonato_ano, codigo_api=codigo_api)
    novo = Bolao(nome=nome, campeonato=campeonato, criador=usuario,
                 permite_palpite_proprio=False, permite_lancamento_por_responsavel=True)
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
