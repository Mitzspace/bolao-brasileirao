"""Logo (bandeira/escudo) e sigla de cada seleção, para a Copa do Mundo e outras competições de seleções.

Chave: nome normalizado (services.sync._normalizar_time) em português, como a ESPN devolve com lang=pt.
Valor: (arquivo do logo no CDN da ESPN, sigla). O logo é o código de país de 3 letras em
https://a.espncdn.com/i/teamlogos/countries/500/{codigo}.png; um caminho com "/" é usado como está
(ex.: Curaçao, que a ESPN guarda como time de futebol). Edite aqui para trocar um logo.
"""
CDN_SELECOES = 'https://a.espncdn.com/i/teamlogos'

SELECOES = {
    'africa do sul': ('rsa', 'RSA'), 'alemanha': ('ger', 'ALE'), 'argelia': ('alg', 'ALG'),
    'argentina': ('arg', 'ARG'), 'arabia saudita': ('ksa', 'ARS'), 'australia': ('aus', 'AUS'),
    'austria': ('aut', 'AUT'), 'belgica': ('bel', 'BEL'), 'bosnia e herzegovina': ('bih', 'BIH'),
    'brasil': ('bra', 'BRA'), 'cabo verde': ('cpv', 'CPV'), 'canada': ('can', 'CAN'),
    'catar': ('qat', 'CAT'), 'colombia': ('col', 'COL'), 'coreia do sul': ('kor', 'KOR'),
    'costa do marfim': ('civ', 'CDM'), 'croacia': ('cro', 'CRO'), 'curacao': ('soccer/500/11678', 'CUW'),
    'egito': ('egy', 'EGI'), 'equador': ('ecu', 'EQU'), 'escocia': ('sco', 'ESC'),
    'espanha': ('esp', 'ESP'), 'estados unidos': ('usa', 'EUA'), 'franca': ('fra', 'FRA'),
    'gana': ('gha', 'GAN'), 'haiti': ('hai', 'HAI'), 'holanda': ('ned', 'HOL'),
    'inglaterra': ('eng', 'ING'), 'iraque': ('irq', 'IRQ'), 'ira': ('irn', 'IRA'),
    'japao': ('jpn', 'JAP'), 'jordania': ('jor', 'JOR'), 'marrocos': ('mar', 'MAR'),
    'mexico': ('mex', 'MEX'), 'noruega': ('nor', 'NOR'), 'nova zelandia': ('nzl', 'NZL'),
    'panama': ('pan', 'PAN'), 'paraguai': ('par', 'PAR'), 'portugal': ('por', 'POR'),
    'republica democratica do congo': ('rdc', 'RDC'), 'republica tcheca': ('cze', 'TCH'),
    'senegal': ('sen', 'SEN'), 'suecia': ('swe', 'SUE'), 'suica': ('sui', 'SUI'),
    'tunisia': ('tun', 'TUN'), 'turquia': ('tur', 'TUR'), 'uruguai': ('uru', 'URU'),
    'uzbequistao': ('uzb', 'UZB'),
    # Seleções que costumam aparecer em eliminatórias e outras edições.
    'bolivia': ('bol', 'BOL'), 'camaroes': ('cmr', 'CMR'), 'chile': ('chi', 'CHI'),
    'china': ('chn', 'CHN'), 'coreia do norte': ('prk', 'PRK'), 'costa rica': ('crc', 'CRC'),
    'dinamarca': ('den', 'DIN'), 'el salvador': ('slv', 'SLV'), 'eslovaquia': ('svk', 'SVK'),
    'eslovenia': ('svn', 'SVN'), 'gales': ('wal', 'PAI'), 'grecia': ('gre', 'GRE'),
    'honduras': ('hon', 'HON'), 'hungria': ('hun', 'HUN'), 'irlanda': ('irl', 'IRL'),
    'islandia': ('isl', 'ISL'), 'italia': ('ita', 'ITA'), 'jamaica': ('jam', 'JAM'),
    'nigeria': ('nga', 'NGA'), 'peru': ('per', 'PER'), 'polonia': ('pol', 'POL'),
    'romenia': ('rou', 'ROM'), 'russia': ('rus', 'RUS'), 'servia': ('srb', 'SER'),
    'trinidad e tobago': ('tri', 'TRI'), 'ucrania': ('ukr', 'UCR'), 'venezuela': ('ven', 'VEN'),
}


def logo_selecao(chave):
    """URL do logo da seleção (chave normalizada) ou None."""
    item = SELECOES.get(chave)
    if not item:
        return None
    arquivo = item[0]
    return f'{CDN_SELECOES}/{arquivo}.png' if '/' in arquivo else f'{CDN_SELECOES}/countries/500/{arquivo}.png'


def sigla_selecao(chave):
    item = SELECOES.get(chave)
    return item[1] if item else None
