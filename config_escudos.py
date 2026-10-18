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

# Times de copas e estaduais (Libertadores, Sul-Americana, Copa do Brasil, Mineiro 2025-2026):
# logos da ESPN em 160 px. Fica de fora 'guarani': Guarani (BRA) e Guaraní (PAR) têm o mesmo
# nome normalizado e o escudo por nome mostraria o errado para um deles.
ESCUDOS_COPAS = {
    '2 de mayo': 'escudos/2-de-mayo.png',  # 2 de Mayo
    'abc': 'escudos/abc.png',  # ABC
    'academia puerto cabello': 'escudos/academia-puerto-cabello.png',  # Academia Puerto Cabello
    'adt': 'escudos/adt.png',  # ADT
    'alianza atletico': 'escudos/alianza-atletico.png',  # Alianza Atlético
    'alianza lima': 'escudos/alianza-lima.png',  # Alianza Lima
    'always ready': 'escudos/always-ready.png',  # Always Ready
    'amazonas': 'escudos/amazonas.png',  # Amazonas
    'america de cali': 'escudos/america-de-cali.png',  # América de Cali
    'america mg': 'escudos/america-mg.png',  # América Mineiro
    'america rn': 'escudos/america-rn.png',  # América-RN
    'anapolis': 'escudos/anapolis.png',  # Anápolis
    'aparecidense': 'escudos/aparecidense.png',  # Aparecidense
    'argentinos juniors': 'escudos/argentinos-juniors.png',  # Argentinos Juniors
    'asa': 'escudos/asa.png',  # ASA
    'athletic': 'escudos/athletic.png',  # Athletic
    'atletico bucaramanga': 'escudos/atletico-bucaramanga.png',  # Atlético Bucaramanga
    'atletico go': 'escudos/atletico-go.png',  # Atlético Goianiense
    'atletico grau': 'escudos/atletico-grau.png',  # Atlético Grau
    'atletico junior': 'escudos/atletico-junior.png',  # Atlético Junior
    'atletico nacional': 'escudos/atletico-nacional.png',  # Atlético Nacional
    'aucas': 'escudos/aucas.png',  # Aucas
    'audax italiano': 'escudos/audax-italiano.png',  # Audax Italiano
    'aurora': 'escudos/aurora.png',  # Aurora
    'avai': 'escudos/avai.png',  # Avaí
    'barcelona': 'escudos/barcelona.png',  # Barcelona SC
    'barracas central': 'escudos/barracas-central.png',  # Barracas Central
    'blooming': 'escudos/blooming.png',  # Blooming
    'boavista': 'escudos/boavista.png',  # Boavista
    'boca juniors': 'escudos/boca-juniors.png',  # Boca Juniors
    'bolivar': 'escudos/bolivar.png',  # Bolívar
    'boston river': 'escudos/boston-river.png',  # Boston River
    'botafogo pb': 'escudos/botafogo-pb.png',  # Botafogo-PB
    'brusque': 'escudos/brusque.png',  # Brusque
    'carabobo': 'escudos/carabobo.png',  # Carabobo
    'caracas': 'escudos/caracas.png',  # Caracas FC
    'caxias do sul': 'escudos/caxias-do-sul.png',  # Caxias do Sul
    'ceara': 'escudos/ceara.png',  # Ceará
    'ceilandia': 'escudos/ceilandia.png',  # Ceilândia
    'central cordoba santiago del estero': 'escudos/central-cordoba-santiago-del-estero.png',  # Central Córdoba (Santiago del Estero)
    'cerro largo': 'escudos/cerro-largo.png',  # Cerro Largo
    'cerro porteno': 'escudos/cerro-porteno.png',  # Cerro Porteño
    'cianorte': 'escudos/cianorte.png',  # Cianorte
    'cienciano del cusco': 'escudos/cienciano-del-cusco.png',  # Cienciano del Cusco
    'club olimpia': 'escudos/club-olimpia.png',  # Club Olimpia
    'cobresal': 'escudos/cobresal.png',  # Cobresal
    'colo colo': 'escudos/colo-colo.png',  # Colo Colo
    'confianca': 'escudos/confianca.png',  # Confiança
    'coquimbo unido': 'escudos/coquimbo-unido.png',  # Coquimbo Unido
    'crb': 'escudos/crb.png',  # CRB
    'criciuma': 'escudos/criciuma.png',  # Criciúma
    'csa': 'escudos/csa.png',  # CSA
    'cuiaba': 'escudos/cuiaba.png',  # Cuiabá
    'cusco': 'escudos/cusco.png',  # Cusco FC
    'danubio': 'escudos/danubio.png',  # Danubio
    'defensa y justicia': 'escudos/defensa-y-justicia.png',  # Defensa y Justicia
    'defensor sporting': 'escudos/defensor-sporting.png',  # Defensor Sporting
    'democrata gv': 'escudos/democrata-gv.png',  # Democrata GV
    'deportes iquique': 'escudos/deportes-iquique.png',  # Deportes Iquique
    'deportes tolima': 'escudos/deportes-tolima.png',  # Deportes Tolima
    'deportivo cuenca': 'escudos/deportivo-cuenca.png',  # Deportivo Cuenca
    'deportivo garcilaso': 'escudos/deportivo-garcilaso.png',  # Deportivo Garcilaso
    'deportivo la guaira': 'escudos/deportivo-la-guaira.png',  # Deportivo La Guaira
    'deportivo recoleta': 'escudos/deportivo-recoleta.png',  # Deportivo Recoleta
    'deportivo riestra': 'escudos/deportivo-riestra.png',  # Deportivo Riestra
    'deportivo tachira': 'escudos/deportivo-tachira.png',  # Deportivo Táchira
    'el nacional': 'escudos/el-nacional.png',  # El Nacional
    'estudiantes de la plata': 'escudos/estudiantes-de-la-plata.png',  # Estudiantes de La Plata
    'everton cd': 'escudos/everton-cd.png',  # Everton CD
    'figueirense': 'escudos/figueirense.png',  # Figueirense
    'fortaleza': 'escudos/fortaleza.png',  # Fortaleza
    'godoy cruz antonio tomba': 'escudos/godoy-cruz-antonio-tomba.png',  # Godoy Cruz Antonio Tomba
    'goias': 'escudos/goias.png',  # Goiás
    'guabira': 'escudos/guabira.png',  # Guabirá
    'gv san jose': 'escudos/gv-san-jose.png',  # GV San José
    'huachipato': 'escudos/huachipato.png',  # Huachipato
    'huracan': 'escudos/huracan.png',  # Huracán
    'independiente': 'escudos/independiente.png',  # Independiente
    'independiente del valle': 'escudos/independiente-del-valle.png',  # Independiente del Valle
    'independiente medellin': 'escudos/independiente-medellin.png',  # Independiente Medellín
    'independiente petrolero': 'escudos/independiente-petrolero.png',  # Independiente Petrolero
    'independiente rivadavia': 'escudos/independiente-rivadavia.png',  # Independiente Rivadavia
    'independiente santa fe': 'escudos/independiente-santa-fe.png',  # Independiente Santa Fe
    'inter de limeira': 'escudos/inter-de-limeira.png',  # Inter de Limeira
    'itabaiana': 'escudos/itabaiana.png',  # Itabaiana
    'joinville': 'escudos/joinville.png',  # Joinville
    'juazeirense': 'escudos/juazeirense.png',  # Juazeirense
    'juventud': 'escudos/juventud.png',  # Juventud
    'juventude': 'escudos/juventude.png',  # Juventude
    'lanus': 'escudos/lanus.png',  # Lanús
    'libertad': 'escudos/libertad.png',  # Libertad
    'libertad ecuador': 'escudos/libertad-ecuador.png',  # Libertad (Ecuador)
    'liga de quito': 'escudos/liga-de-quito.png',  # Liga de Quito
    'liverpool': 'escudos/liverpool.png',  # Liverpool
    'londrina': 'escudos/londrina.png',  # Londrina
    'macara': 'escudos/macara.png',  # Macará
    'madureira': 'escudos/madureira.png',  # Madureira
    'manaus': 'escudos/manaus.png',  # Manaus
    'melgar': 'escudos/melgar.png',  # Melgar
    'metropolitanos': 'escudos/metropolitanos.png',  # Metropolitanos
    'millonarios': 'escudos/millonarios.png',  # Millonarios
    'monagas': 'escudos/monagas.png',  # Monagas SC
    'montevideo city torque': 'escudos/montevideo-city-torque.png',  # Montevideo City Torque
    'montevideo wanderers': 'escudos/montevideo-wanderers.png',  # Montevideo Wanderers
    'mushuc runa': 'escudos/mushuc-runa.png',  # Mushuc Runa
    'nacional': 'escudos/nacional.png',  # Nacional
    'nacional asuncion': 'escudos/nacional-asuncion.png',  # Nacional Asunción
    'nacional de manaus': 'escudos/nacional-de-manaus.png',  # Nacional de Manaus
    'nacional potosi': 'escudos/nacional-potosi.png',  # Nacional Potosí
    'nautico': 'escudos/nautico.png',  # Náutico
    'nova iguacu': 'escudos/nova-iguacu.png',  # Nova Iguaçu
    'novorizontino': 'escudos/novorizontino.png',  # Novorizontino
    'nublense': 'escudos/nublense.png',  # Ñublense
    'o higgins': 'escudos/o-higgins.png',  # O'Higgins
    'once caldas': 'escudos/once-caldas.png',  # Once Caldas
    'operario pr': 'escudos/operario-pr.png',  # Operário PR
    'orense': 'escudos/orense.png',  # Orense
    'palestino': 'escudos/palestino.png',  # Palestino
    'parnahyba': 'escudos/parnahyba.png',  # Parnahyba
    'paysandu': 'escudos/paysandu.png',  # Paysandu
    'penarol': 'escudos/penarol.png',  # Peñarol
    'platense': 'escudos/platense.png',  # Platense
    'ponte preta': 'escudos/ponte-preta.png',  # Ponte Preta
    'portuguesa': 'escudos/portuguesa.png',  # Portuguesa
    'portuguesa rj': 'escudos/portuguesa-rj.png',  # Portuguesa-RJ
    'racing club': 'escudos/racing-club.png',  # Racing Club
    'racing montevideo': 'escudos/racing-montevideo.png',  # Racing (Montevideo)
    'river plate': 'escudos/river-plate.png',  # River Plate
    'rosario central': 'escudos/rosario-central.png',  # Rosário Central
    'sampaio correa': 'escudos/sampaio-correa.png',  # Sampaio Corrêa
    'san antonio bulo bulo': 'escudos/san-antonio-bulo-bulo.png',  # San Antonio Bulo Bulo
    'san lorenzo': 'escudos/san-lorenzo.png',  # San Lorenzo
    'santa cruz': 'escudos/santa-cruz.png',  # Santa Cruz
    'sao bernardo': 'escudos/sao-bernardo.png',  # São Bernardo
    'sao jose rs': 'escudos/sao-jose-rs.png',  # São José-RS
    'sao luiz rs': 'escudos/sao-luiz-rs.png',  # São Luiz-RS
    'sao raimundo rr': 'escudos/sao-raimundo-rr.png',  # São Raimundo-RR
    'sergipe': 'escudos/sergipe.png',  # Sergipe SE
    'sport': 'escudos/sport.png',  # Sport
    'sporting cristal': 'escudos/sporting-cristal.png',  # Sporting Cristal
    'sportivo ameliano': 'escudos/sportivo-ameliano.png',  # Sportivo Ameliano
    'sportivo luqueno': 'escudos/sportivo-luqueno.png',  # Sportivo Luqueño
    'sportivo trinidense': 'escudos/sportivo-trinidense.png',  # Sportivo Trinidense
    'talleres cordoba': 'escudos/talleres-cordoba.png',  # Talleres (Córdoba)
    'the strongest': 'escudos/the-strongest.png',  # The Strongest
    'tigre': 'escudos/tigre.png',  # Tigre
    'tombense': 'escudos/tombense.png',  # Tombense
    'uberlandia': 'escudos/uberlandia.png',  # Uberlândia
    'ucv': 'escudos/ucv.png',  # UCV FC
    'union espanola': 'escudos/union-espanola.png',  # Unión Española
    'union santa fe': 'escudos/union-santa-fe.png',  # Unión (Santa Fe)
    'universidad catolica': 'escudos/universidad-catolica.png',  # Universidad Católica
    'universidad catolica quito': 'escudos/universidad-catolica-quito.png',  # Universidad Católica (Quito)
    'universidad de chile': 'escudos/universidad-de-chile.png',  # Universidad de Chile
    'universitario': 'escudos/universitario.png',  # Universitario
    'universitario de vinto': 'escudos/universitario-de-vinto.png',  # Universitario de Vinto
    'urt': 'escudos/urt.png',  # URT
    'velez sarsfield': 'escudos/velez-sarsfield.png',  # Vélez Sarsfield
    'vila nova': 'escudos/vila-nova.png',  # Vila Nova
    'villa nova mg': 'escudos/villa-nova-mg.png',  # Villa Nova-MG
    'volta redonda': 'escudos/volta-redonda.png',  # Volta Redonda
    'votuporanguense s20': 'escudos/votuporanguense-s20.png',  # Votuporanguense S20
    'ypiranga': 'escudos/ypiranga.png',  # Ypiranga
}
SIGLAS_COPAS = {
    '2 de mayo': 'MAY',
    'abc': 'ABC',
    'academia puerto cabello': 'APC',
    'adt': 'ADT',
    'alianza atletico': 'AAT',
    'alianza lima': 'ALM',
    'always ready': 'CAR',
    'amazonas': 'AMA',
    'america de cali': 'AME',
    'america mg': 'AMG',
    'america rn': 'ARN',
    'anapolis': 'ANA',
    'aparecidense': 'APA',
    'argentinos juniors': 'ARGJ',
    'asa': 'ASA',
    'athletic': 'ACMG',
    'atletico bucaramanga': 'BUC',
    'atletico go': 'AGO',
    'atletico grau': 'AGR',
    'atletico junior': 'JUN',
    'atletico nacional': 'NAL',
    'aucas': 'AUC',
    'audax italiano': 'AUD',
    'aurora': 'AUR',
    'avai': 'AVA',
    'barcelona': 'BAR',
    'barracas central': 'BAR',
    'blooming': 'BLO',
    'boavista': 'BVT',
    'boca juniors': 'CABJ',
    'bolivar': 'BOL',
    'boston river': 'BOS',
    'botafogo pb': 'BPB',
    'brusque': 'BRUS',
    'carabobo': 'CAR',
    'caracas': 'CFC',
    'caxias do sul': 'CAX',
    'ceara': 'CEA',
    'ceilandia': 'CEI',
    'central cordoba santiago del estero': 'CTR',
    'cerro largo': 'CERR',
    'cerro porteno': 'CPT',
    'cianorte': 'CIA',
    'cienciano del cusco': 'CIE',
    'club olimpia': 'OLI',
    'cobresal': 'COB',
    'colo colo': 'COL',
    'confianca': 'CON',
    'coquimbo unido': 'COQ',
    'crb': 'CRB',
    'criciuma': 'CRI',
    'csa': 'CSA',
    'cuiaba': 'CUI',
    'cusco': 'CFC',
    'danubio': 'DAN',
    'defensa y justicia': 'DYJ',
    'defensor sporting': 'DSC',
    'democrata gv': 'DEM',
    'deportes iquique': 'CDI',
    'deportes tolima': 'TOL',
    'deportivo cuenca': 'CLU',
    'deportivo garcilaso': 'GAR',
    'deportivo la guaira': 'DEPO',
    'deportivo recoleta': 'DEP',
    'deportivo riestra': 'RIE',
    'deportivo tachira': 'TAC',
    'el nacional': 'ELN',
    'estudiantes de la plata': 'EST',
    'everton cd': 'EVE',
    'figueirense': 'FIG',
    'fortaleza': 'FOR',
    'godoy cruz antonio tomba': 'GCM',
    'goias': 'GOI',
    'guabira': 'GUA',
    'gv san jose': 'GVSJ',
    'huachipato': 'HUA',
    'huracan': 'HUR',
    'independiente': 'IND',
    'independiente del valle': 'IDV',
    'independiente medellin': 'DIM',
    'independiente petrolero': 'CIP',
    'independiente rivadavia': 'RIV',
    'independiente santa fe': 'SFE',
    'inter de limeira': 'ILI',
    'itabaiana': 'ITA',
    'joinville': 'JEC',
    'juazeirense': 'JUA',
    'juventud': 'JUV',
    'juventude': 'JUV',
    'lanus': 'LAN',
    'libertad': 'LIB',
    'libertad ecuador': 'LIB',
    'liga de quito': 'LDU',
    'liverpool': 'LIV',
    'londrina': 'LON',
    'macara': 'MAC',
    'madureira': 'MAD',
    'manaus': 'MAN',
    'melgar': 'MGR',
    'metropolitanos': 'MET',
    'millonarios': 'MIL',
    'monagas': 'MSC',
    'montevideo city torque': 'MCT',
    'montevideo wanderers': 'WAN',
    'mushuc runa': 'MUS',
    'nacional': 'NAC',
    'nacional asuncion': 'NAC',
    'nacional de manaus': 'NAM',
    'nacional potosi': 'POT',
    'nautico': 'NAU',
    'nova iguacu': 'NOV',
    'novorizontino': 'NOV',
    'nublense': 'ÑUB',
    'o higgins': 'OHI',
    'once caldas': 'CAL',
    'operario pr': 'OPE',
    'orense': 'ORS',
    'palestino': 'PAL',
    'parnahyba': 'PAR',
    'paysandu': 'PAY',
    'penarol': 'PEN',
    'platense': 'PLA',
    'ponte preta': 'PON',
    'portuguesa': 'PTG',
    'portuguesa rj': 'POR',
    'racing club': 'RAC',
    'racing montevideo': 'RAC',
    'river plate': 'RIV',
    'rosario central': 'ROS',
    'sampaio correa': 'SAM',
    'san antonio bulo bulo': 'BULO',
    'san lorenzo': 'SLZ',
    'santa cruz': 'STC',
    'sao bernardo': 'BER',
    'sao jose rs': 'SJO',
    'sao luiz rs': 'SLU',
    'sao raimundo rr': 'SRA',
    'sergipe': 'SSE',
    'sport': 'SPO',
    'sporting cristal': 'SCR',
    'sportivo ameliano': 'CSA',
    'sportivo luqueno': 'LUQ',
    'sportivo trinidense': 'CST',
    'talleres cordoba': 'TALL',
    'the strongest': 'STR',
    'tigre': 'TIG',
    'tombense': 'TOM',
    'uberlandia': 'UBE',
    'ucv': 'UCV',
    'union espanola': 'UNI',
    'union santa fe': 'USF',
    'universidad catolica': 'CDUC',
    'universidad catolica quito': 'UCA',
    'universidad de chile': 'UCH',
    'universitario': 'UNI',
    'universitario de vinto': 'UDV',
    'urt': 'URT',
    'velez sarsfield': 'VEL',
    'vila nova': 'VIL',
    'villa nova mg': 'VNMG',
    'volta redonda': 'VRE',
    'votuporanguense s20': 'VOT',
    'ypiranga': 'YPI',
}

# Os da Série A (acima) prevalecem.
ESCUDOS_POR_NOME = {**ESCUDOS_COPAS, **ESCUDOS_POR_NOME}
SIGLAS_POR_NOME = {**SIGLAS_COPAS, **SIGLAS_POR_NOME}
