"""Clássicos do bolão: confrontos que valem a pontuação de jogo clássico.

A lista é a mesma que já vinha sendo marcada à mão (16 confrontos, ida e volta,
em qualquer mando). Os nomes passam por services.sync._normalizar_time, então
"CA Mineiro", "Atlético-MG" e "Atletico Mineiro" são o mesmo time, e
"SC Corinthians Paulista" é o mesmo que "Corinthians".

Onde é aplicado: só ao CRIAR um jogo (sincronização com a API, cadastro manual e
importação de planilha). Editar um jogo continua valendo o que o responsável
marcou, então desmarcar um clássico à mão não é desfeito depois.
Para acertar jogos que já existem: python -m scripts.marcar_classicos
"""
from services.sync import _normalizar_time

# Para incluir um clássico novo, basta acrescentar o par aqui (a ordem não importa).
CLASSICOS = (
    ('Corinthians', 'São Paulo'),
    ('Corinthians', 'Palmeiras'),
    ('Corinthians', 'Santos'),
    ('Palmeiras', 'São Paulo'),
    ('Palmeiras', 'Santos'),
    ('Santos', 'São Paulo'),
    ('Flamengo', 'Fluminense'),
    ('Flamengo', 'Vasco'),
    ('Flamengo', 'Botafogo'),
    ('Fluminense', 'Vasco'),
    ('Fluminense', 'Botafogo'),
    ('Botafogo', 'Vasco'),
    ('Grêmio', 'Internacional'),
    ('Atlético-MG', 'Cruzeiro'),
    ('Bahia', 'Vitória'),
    ('Athletico-PR', 'Coritiba'),
)

_PARES = frozenset(frozenset((_normalizar_time(a), _normalizar_time(b))) for a, b in CLASSICOS)


def eh_classico(time_casa, time_fora):
    """True se o confronto (em qualquer mando) está na lista de clássicos."""
    return frozenset((_normalizar_time(time_casa), _normalizar_time(time_fora))) in _PARES
