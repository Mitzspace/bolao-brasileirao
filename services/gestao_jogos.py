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


def criar_jogo(time_casa, time_fora, rodada_id, data, classico, pode_penaltis=False):
    casa, fora, rodada, data = validar_dados_jogo(time_casa, time_fora, rodada_id, data)
    # Clássico da lista (services/classicos.py) é marcado sozinho; a caixa marcada vale para outros confrontos.
    jogo = Jogo(time_casa=casa, time_fora=fora, rodada_id=rodada.id,
                especial=bool(classico) or eh_classico(casa, fora), data=data,
                pode_penaltis=bool(pode_penaltis))
    db.session.add(jogo)
    db.session.commit()
    return jogo


def editar_jogo(jogo, time_casa, time_fora, rodada_id, data, classico, encerrado=None, pode_penaltis=None):
    """pode_penaltis=None mantém o valor atual (clientes antigos não enviam o campo)."""
    casa, fora, rodada, data = validar_dados_jogo(time_casa, time_fora, rodada_id, data)
    jogo.time_casa = casa
    jogo.time_fora = fora
    jogo.rodada_id = rodada.id
    jogo.especial = bool(classico)
    if encerrado is not None:
        jogo.encerrado = bool(encerrado)
    if pode_penaltis is not None:
        jogo.pode_penaltis = bool(pode_penaltis)
        if not jogo.pode_penaltis and jogo.resultado is not None:
            # Sem disputa de pênaltis, o placar dos pênaltis do resultado deixa de existir
            # (e os palpites de pênaltis deixam de pontuar). Os palpites ficam como estão.
            jogo.resultado.penaltis_casa_real = jogo.resultado.penaltis_fora_real = None
    jogo.data = data
    db.session.commit()
    return jogo


def definir_encerrado(jogo, encerrado):
    jogo.encerrado = bool(encerrado)
    db.session.commit()


def validar_penaltis(jogo, casa, fora):
    """(casa, fora) inteiros ou (None, None) se ambos vazios; levanta ValueError."""
    vazio = [v is None or str(v).strip() == '' for v in (casa, fora)]
    if all(vazio):
        return None, None
    if not jogo.pode_penaltis:
        raise ValueError('Este jogo não tem disputa de pênaltis. Marque "Pode ter pênaltis" no jogo primeiro.')
    if any(vazio):
        raise ValueError('Informe os dois lados do placar dos pênaltis (ou deixe ambos vazios).')
    casa, fora = inteiro(casa, 'Pênaltis da casa', 0, 99), inteiro(fora, 'Pênaltis de fora', 0, 99)
    if casa == fora:
        raise ValueError('A disputa de pênaltis não termina empatada.')
    return casa, fora


def lancar_resultado(jogo, gols_casa, gols_fora, primeiro_gol=None, penaltis=None):
    """penaltis: (casa, fora) do placar dos pênaltis; None mantém o que já estava gravado."""
    gols_casa, gols_fora = placar(gols_casa, gols_fora)
    if penaltis is not None:
        penaltis = validar_penaltis(jogo, *penaltis)
    resultado = Resultado.query.filter_by(jogo_id=jogo.id).first()
    if resultado is None:
        resultado = Resultado(jogo_id=jogo.id)
        db.session.add(resultado)
    resultado.gols_casa_real = gols_casa
    resultado.gols_fora_real = gols_fora
    resultado.primeiro_gol_real = (primeiro_gol or '').strip() or None
    if penaltis is not None:
        resultado.penaltis_casa_real, resultado.penaltis_fora_real = penaltis
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
