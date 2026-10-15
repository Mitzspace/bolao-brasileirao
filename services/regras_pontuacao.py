"""Regras de pontuação: valores padrão e regras próprias de cada bolão."""
from types import MappingProxyType

# Valores padrão (também os de todo bolão criado antes das regras editáveis).
REGRAS_PONTUACAO = MappingProxyType({
    "comum_exato": 3, "comum_resultado": 1,
    "classico_exato": 5, "classico_resultado": 3, "primeiro_gol": 2,
})

# chave da regra -> coluna em Bolao
COLUNAS = {chave: f"pontos_{chave}" for chave in REGRAS_PONTUACAO}
MAXIMO = 99


def regras_do_bolao(bolao):
    """Regras do bolão; sem bolão (ou coluna ausente) usa os valores padrão."""
    if bolao is None:
        return REGRAS_PONTUACAO
    return MappingProxyType({chave: (getattr(bolao, coluna, None) if getattr(bolao, coluna, None) is not None
                                     else REGRAS_PONTUACAO[chave]) for chave, coluna in COLUNAS.items()})


def regras_do_palpite(palpite):
    participacao = getattr(palpite, "participacao", None)
    return regras_do_bolao(getattr(participacao, "bolao", None))


def validar_regras(valores):
    """Recebe {chave: valor} com todas as chaves; devolve inteiros ou levanta ValueError."""
    if not isinstance(valores, dict):
        raise ValueError("Informe as regras de pontuação.")
    regras = {}
    for chave in REGRAS_PONTUACAO:
        valor = valores.get(chave)
        if isinstance(valor, bool) or not isinstance(valor, (int, str)) or not str(valor).strip().isdecimal():
            raise ValueError(f"Informe um número inteiro de 0 a {MAXIMO} em todas as regras.")
        numero = int(str(valor).strip())
        if numero > MAXIMO:
            raise ValueError(f"Informe um número inteiro de 0 a {MAXIMO} em todas as regras.")
        regras[chave] = numero
    if regras["comum_exato"] < regras["comum_resultado"] or regras["classico_exato"] < regras["classico_resultado"]:
        raise ValueError("O placar exato precisa valer pelo menos o mesmo que acertar só o resultado.")
    return regras


def aplicar_regras(bolao, regras):
    for chave, coluna in COLUNAS.items():
        setattr(bolao, coluna, regras[chave])
