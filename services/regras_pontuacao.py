"""Valores únicos, também disponibilizados aos templates."""
from types import MappingProxyType

REGRAS_PONTUACAO = MappingProxyType({
    "comum_exato": 3, "comum_resultado": 1,
    "classico_exato": 5, "classico_resultado": 3, "primeiro_gol": 2,
})
