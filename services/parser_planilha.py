"""Leitura compartilhada dos formatos de jogos e palpites das planilhas."""
import re

PADRAO_PALPITE = re.compile(r"(\d+)\s*[xX]\s*(\d+)")
PALAVRAS_IGNORAR = ('pontua', 'ponto', 'cravada', 'acerto', 'total', 'totais', 'classificacao', 'ranking')


def extrair_num_rodada(nome):
    m = re.search(r"(\d+)", str(nome))
    return int(m.group(1)) if m else 999


def parse_placar(texto):
    """
    Tenta extrair time_casa, time_fora, gols_casa_real, gols_fora_real de formatos como:
      'Atlético-MG 2x2 Palmeiras'
      'Atlético-MG x Botafogo [1x1]'
      'Corinthians x São Paulo ★ [3x2]'
      'Fluminense x Coritiba'
    """
    if not texto:
        return None, None, None, None, False

    str_texto = str(texto).strip()
    especial = "★" in str_texto or "*" in str_texto
    limpo = str_texto.replace("★", "").replace("*", "").strip()

    # Formato com colchetes: TimeA x TimeB [1x1]
    m_colchetes = re.match(r"^(.+?)\s*\[(\d+)\s*[xX]\s*(\d+)\]$", limpo)
    if m_colchetes:
        confronto, gc, gf = m_colchetes.groups()
        m_times = re.match(r"^(.+?)\s+[xX]\s+(.+)$", confronto.strip())
        if m_times:
            return m_times.group(1).strip(), m_times.group(2).strip(), int(gc), int(gf), especial
        return confronto.strip(), "Adversário", int(gc), int(gf), especial

    # Formato tradicional com placar no meio: TimeA 2x1 TimeB
    m_meio = re.match(r"^(.+?)\s+(\d+)\s*[xX]\s*(\d+)\s+(.+)$", limpo)
    if m_meio:
        tc, gc, gf, tf = m_meio.groups()
        return tc.strip(), tf.strip(), int(gc), int(gf), especial

    # Formato sem placar: TimeA x TimeB
    m_sem = re.match(r"^(.+?)\s+[xX]\s+(.+)$", limpo)
    if m_sem:
        tc, tf = m_sem.groups()
        return tc.strip(), tf.strip(), None, None, especial

    return None, None, None, None, especial


