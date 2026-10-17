"""Edição de um bolão já criado: nome e situação (em andamento, finalizado, desistido).

Os campeonatos do mesmo bolão (grupo) aparecem como um único bolão na interface e dividem
o nome, então nome e situação valem para o grupo inteiro.
"""
from models import Bolao

# 'ativo' é o valor que sempre existiu no banco; na tela aparece como "Em andamento".
STATUS_BOLAO = ('ativo', 'finalizado', 'desistido')
ROTULOS_STATUS = {'ativo': 'em andamento', 'finalizado': 'finalizado', 'desistido': 'desistido'}
TAMANHO_MAXIMO_NOME = 100


def validar_nome(nome):
    """Tira espaços extras e confere o tamanho; levanta ValueError com a mensagem para a tela."""
    if not isinstance(nome, str):
        raise ValueError('Informe o nome do bolão.')
    nome = ' '.join(nome.split())
    if not nome:
        raise ValueError('Informe o nome do bolão.')
    if len(nome) > TAMANHO_MAXIMO_NOME:
        raise ValueError(f'O nome pode ter no máximo {TAMANHO_MAXIMO_NOME} caracteres.')
    return nome


def validar_status(status):
    if status not in STATUS_BOLAO:
        raise ValueError('Situação inválida. Use em andamento, finalizado ou desistido.')
    return status


def editavel(bolao):
    """Bolão finalizado ou desistido fica somente para consulta até voltar para 'em andamento'."""
    return bolao.status == 'ativo'


def mensagem_bloqueio(bolao):
    return (f'Este bolão está {ROTULOS_STATUS.get(bolao.status, bolao.status)} e não pode ser alterado. '
            'Volte-o para "Em andamento" na tela Bolões para editar.')


def boloes_do_grupo(bolao):
    raiz = bolao.grupo_raiz_id
    return Bolao.query.filter((Bolao.id == raiz) | (Bolao.grupo_id == raiz)).order_by(Bolao.id).all()


def renomear(bolao, nome):
    """Renomeia o grupo inteiro (sem commit). Devolve (nome_antigo, nome_novo, boloes)."""
    nome = validar_nome(nome)
    boloes = boloes_do_grupo(bolao)
    antigo = bolao.nome
    for b in boloes:
        b.nome = nome
    return antigo, nome, boloes


def alterar_status(bolao, status):
    """Muda a situação do grupo inteiro (sem commit). Devolve (status_antigo, boloes)."""
    status = validar_status(status)
    boloes = boloes_do_grupo(bolao)
    antigo = bolao.status
    for b in boloes:
        b.status = status
    return antigo, boloes
