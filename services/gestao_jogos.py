"""Regras de jogos e resultados usadas pelas telas atuais e pela nova interface.

Extraído de routes/admin.py sem mudar o comportamento. A auditoria
(services/auditoria.py) mantém Resultado.primeiro_gol_real e Jogo.primeiro_marcador
sincronizados, como antes.
"""
from database import db
from models import Jogo, Resultado, Rodada
from services.classicos import eh_classico
from services.contexto_bolao import validar_rodada
from services.validacao_formularios import data_jogo, inteiro, placar, texto


def validar_dados_jogo(time_casa, time_fora, rodada_id, data):
    """Retorna (casa, fora, rodada, data) ou lança ValueError; rodada de outro bolão dá 404."""
    casa = texto(time_casa, 'Time da casa')
    fora = texto(time_fora, 'Time de fora')
    rodada_id = inteiro(rodada_id, 'Rodada', 1)
    data = data_jogo(data)
    rodada = Rodada.query.get_or_404(rodada_id)
    validar_rodada(rodada)
    return casa, fora, rodada, data


def criar_jogo(time_casa, time_fora, rodada_id, data, classico):
    casa, fora, rodada, data = validar_dados_jogo(time_casa, time_fora, rodada_id, data)
    # Clássico da lista (services/classicos.py) é marcado sozinho; a caixa marcada vale para outros confrontos.
    jogo = Jogo(time_casa=casa, time_fora=fora, rodada_id=rodada.id,
                especial=bool(classico) or eh_classico(casa, fora), data=data)
    db.session.add(jogo)
    db.session.commit()
    return jogo


def editar_jogo(jogo, time_casa, time_fora, rodada_id, data, classico, encerrado=None):
    casa, fora, rodada, data = validar_dados_jogo(time_casa, time_fora, rodada_id, data)
    jogo.time_casa = casa
    jogo.time_fora = fora
    jogo.rodada_id = rodada.id
    jogo.especial = bool(classico)
    if encerrado is not None:
        jogo.encerrado = bool(encerrado)
    jogo.data = data
    db.session.commit()
    return jogo


def definir_encerrado(jogo, encerrado):
    jogo.encerrado = bool(encerrado)
    db.session.commit()


def lancar_resultado(jogo, gols_casa, gols_fora, primeiro_gol=None):
    gols_casa, gols_fora = placar(gols_casa, gols_fora)
    resultado = Resultado.query.filter_by(jogo_id=jogo.id).first()
    if resultado is None:
        resultado = Resultado(jogo_id=jogo.id)
        db.session.add(resultado)
    resultado.gols_casa_real = gols_casa
    resultado.gols_fora_real = gols_fora
    resultado.primeiro_gol_real = (primeiro_gol or '').strip() or None
    db.session.commit()
    return resultado


def excluir_jogo(jogo):
    """Exclui jogo sem palpites. Lança ValueError se houver histórico."""
    if jogo.palpites:
        raise ValueError('Este jogo possui palpites e histórico e não pode ser excluído.')
    if jogo.resultado:
        db.session.delete(jogo.resultado)
    db.session.delete(jogo)
    db.session.commit()
