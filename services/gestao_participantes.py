"""Consulta da gestão de participantes, sem alterar a fórmula de pontuação."""
import unicodedata

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from models import BonusRodada, Jogo, Palpite, Participacao
from services.pontuacao import calcular_pontuacao
from services.elegibilidade import palpite_elegivel, dentro_do_periodo


def normalizar_nome(nome):
    sem_acentos = ''.join(c for c in unicodedata.normalize('NFKD', nome)
                          if not unicodedata.combining(c))
    return ' '.join(sem_acentos.casefold().split())


def homonimos(bolao_id, nome, ignorar_id=None):
    chave = normalizar_nome(nome)
    return [p for p in Participacao.query.filter_by(bolao_id=bolao_id).all()
            if p.id != ignorar_id and normalizar_nome(p.nome_exibicao) == chave]


def validar_dados_participante(bolao_id, nome, email, ignorar_id=None):
    from utils import validar_email
    erros = {}
    if not 2 <= len(nome) <= 100:
        erros['nome_exibicao'] = 'Informe um nome entre 2 e 100 caracteres.'
    elif homonimos(bolao_id, nome, ignorar_id):
        erros['nome_exibicao'] = 'Já existe participante com esse nome neste bolão.'
    if email:
        if len(email) > 100 or not validar_email(email):
            erros['email'] = 'Informe um e-mail válido com até 100 caracteres.'
        elif Participacao.query.filter(Participacao.bolao_id == bolao_id,
                func.lower(Participacao.email) == email,
                Participacao.id != ignorar_id if ignorar_id is not None else True).first():
            erros['email'] = 'Já existe participante com esse e-mail neste bolão.'
    return erros


def totais_participantes(bolao_id, pessoas):
    # Contagem inclui os guardados; pontos consideram apenas os elegíveis.
    totais = {p.id: {'pontos': 0, 'palpites': 0} for p in pessoas}
    palpites = (Palpite.query.join(Participacao).filter(Participacao.bolao_id == bolao_id)
                .options(joinedload(Palpite.jogo).joinedload(Jogo.resultado)).all())
    for palpite in palpites:
        total = totais[palpite.participacao_id]
        total['palpites'] += 1
        if palpite_elegivel(palpite):
            total['pontos'] += calcular_pontuacao(palpite, palpite.jogo, palpite.jogo.resultado).total
    for bonus in (BonusRodada.query.join(Participacao).filter(Participacao.bolao_id == bolao_id)
                  .options(joinedload(BonusRodada.rodada)).all()):
        if dentro_do_periodo(bonus.participacao, bonus.rodada):
            totais[bonus.participacao_id]['pontos'] += bonus.pontos
    return totais
