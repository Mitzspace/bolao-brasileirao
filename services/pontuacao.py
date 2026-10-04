import unicodedata


def normalizar_nome_jogador(valor):
    if not valor:
        return ""

    sem_acentos = unicodedata.normalize("NFKD", valor)
    sem_acentos = "".join(c for c in sem_acentos if not unicodedata.combining(c))
    return " ".join(sem_acentos.casefold().split())


def calcular_pontos(palpite, resultado, especial=False):
    """
    Regras do bolão:

    Jogo normal:
      3 pts — placar exato
      1 pt  — acertou o vencedor (ou empate) sem acertar o placar exato

    Jogo especial (clássico):
      5 pts — placar exato
      3 pts — acertou o vencedor (ou empate) sem acertar o placar exato

    Bônus (qualquer jogo especial):
      +2 pts — acertou o jogador do primeiro gol
    """

    gols_casa  = palpite.gols_casa
    gols_fora  = palpite.gols_fora
    real_casa  = resultado.gols_casa_real
    real_fora  = resultado.gols_fora_real

    pontos = 0

    placar_exato = (gols_casa == real_casa and gols_fora == real_fora)

    if placar_exato:
        pontos = 5 if especial else 3
    else:
        acertou_vencedor = (
            (gols_casa > gols_fora and real_casa > real_fora)
            or (gols_casa < gols_fora and real_casa < real_fora)
            or (gols_casa == gols_fora and real_casa == real_fora)
        )
        if acertou_vencedor:
            pontos = 3 if especial else 1

    # Bônus de primeiro gol (só em jogos especiais)
    if especial and resultado.primeiro_gol_real:
        if normalizar_nome_jogador(palpite.primeiro_gol) == normalizar_nome_jogador(resultado.primeiro_gol_real):
            pontos += 2

    return pontos
