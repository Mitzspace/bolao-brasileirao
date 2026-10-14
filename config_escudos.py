"""Overrides editáveis: caminho relativo a static/ ou URL HTTPS.

Arquivos locais têm prioridade; arquivo ausente usa o crest da API.
As chaves de ESCUDOS_POR_NOME são o nome normalizado (services.sync._normalizar_time),
então "Grêmio", "Gremio FBPA" e "Grêmio" da API apontam para o mesmo arquivo.
"""
ESCUDOS_POR_API_ID = {1768: 'escudos/athletico-pr.png'}
ESCUDOS_POR_NOME = {
    'athletico pr': 'escudos/athletico-pr.png',
    'atletico mg': 'escudos/atletico-mg.png',
    'bahia': 'escudos/bahia.png',
    'botafogo': 'escudos/botafogo.png',
    'chapecoense': 'escudos/chapecoense.png',
    'corinthians': 'escudos/corinthians.png',
    'coritiba': 'escudos/coritiba.png',
    'cruzeiro': 'escudos/cruzeiro.png',
    'flamengo': 'escudos/flamengo.png',
    'fluminense': 'escudos/fluminense.png',
    'gremio': 'escudos/gremio.png',
    'internacional': 'escudos/internacional.png',
    'mirassol': 'escudos/mirassol.png',
    'palmeiras': 'escudos/palmeiras.png',
    'red bull bragantino': 'escudos/red-bull-bragantino.png',
    'remo': 'escudos/remo.png',
    'santos': 'escudos/santos.png',
    'sao paulo': 'escudos/sao-paulo.png',
    'vasco': 'escudos/vasco.png',
    'vitoria': 'escudos/vitoria.png',
}

# Siglas exibidas no celular (padrão da CBF), pela mesma chave normalizada.
SIGLAS_POR_NOME = {
    'athletico pr': 'CAP', 'atletico mg': 'CAM', 'bahia': 'BAH', 'botafogo': 'BOT',
    'chapecoense': 'CHA', 'corinthians': 'COR', 'coritiba': 'CFC', 'cruzeiro': 'CRU',
    'flamengo': 'FLA', 'fluminense': 'FLU', 'gremio': 'GRE', 'internacional': 'INT',
    'mirassol': 'MIR', 'palmeiras': 'PAL', 'red bull bragantino': 'RBB', 'remo': 'REM',
    'santos': 'SAN', 'sao paulo': 'SAO', 'vasco': 'VAS', 'vitoria': 'VIT',
}
