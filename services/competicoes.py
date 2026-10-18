"""Modelos de competição oferecidos na criação do bolão e nomes das rodadas de copa."""
import re

FONTE_FOOTBALL_DATA = "football-data"
FONTE_API_FOOTBALL = "api-football"
FONTE_ESPN = "espn"  # API pública e não oficial da ESPN, gratuita e sem chave
FONTES_API = {FONTE_FOOTBALL_DATA: "football-data.org", FONTE_API_FOOTBALL: "API-Football", FONTE_ESPN: "ESPN"}
# Valor de Jogo.external_fonte de cada provedor.
EXTERNAL_FONTE = {FONTE_FOOTBALL_DATA: "football-data.org", FONTE_API_FOOTBALL: "api-football", FONTE_ESPN: "espn"}


def normalizar_fonte(fonte):
    return fonte if fonte in FONTES_API else FONTE_FOOTBALL_DATA


def normalizar_codigo_api(codigo):
    """Preserva slug ESPN (com ponto), id numérico da API-Football e código em maiúsculas da football-data."""
    codigo = (codigo or "").strip()
    if not codigo:
        return codigo
    if "." in codigo:
        return codigo.casefold()
    if codigo.isdigit():
        return codigo
    return codigo.upper()


MODELOS_COMPETICAO = {
    "brasileirao": {"rotulo": "Brasileirão", "nome": "Brasileirão Série A", "codigo_api": "BSA",
                    "fonte_api": FONTE_FOOTBALL_DATA, "eliminacao": False,
                    "descricao": "Pontos corridos, 38 rodadas."},
    "libertadores": {"rotulo": "Libertadores", "nome": "Copa Libertadores", "codigo_api": "conmebol.libertadores",
                     "fonte_api": FONTE_ESPN, "eliminacao": True,
                     "descricao": "Fases preliminares, fase de grupos e mata-mata."},
    "sulamericana": {"rotulo": "Sul-Americana", "nome": "Copa Sul-Americana", "codigo_api": "conmebol.sudamericana",
                     "fonte_api": FONTE_ESPN, "eliminacao": True,
                     "descricao": "Fase preliminar, fase de grupos, playoffs e mata-mata."},
    "copadobrasil": {"rotulo": "Copa do Brasil", "nome": "Copa do Brasil", "codigo_api": "bra.copa_do_brazil",
                     "fonte_api": FONTE_ESPN, "eliminacao": True,
                     "descricao": "Só mata-mata, da 1ª fase à final."},
    "mineiro": {"rotulo": "Campeonato Mineiro", "nome": "Campeonato Mineiro", "codigo_api": "bra.camp.mineiro",
                "fonte_api": FONTE_ESPN, "eliminacao": True,
                "descricao": "Primeira fase, semifinal e final."},
}

# Copas na football-data.org fora do plano gratuito exigem token pago.
CODIGOS_PLANO_PAGO = {"CLI", "CS"}

# Fases eliminatórias em ordem; numeradas após a última rodada da fase de grupos.
FASES_MATA_MATA = [
    ("PLAYOFFS", "Playoffs"),
    ("PLAYOFF_ROUND", "Playoffs"),
    ("LAST_64", "32 avos de final"),
    ("LAST_32", "16 avos de final"),
    ("ROUND_OF_32", "16 avos de final"),
    ("LAST_16", "Oitavas de final"),
    ("ROUND_OF_16", "Oitavas de final"),
    ("QUARTER_FINALS", "Quartas de final"),
    ("SEMI_FINALS", "Semifinal"),
    ("THIRD_PLACE", "Disputa de 3º lugar"),
    ("FINAL", "Final"),
]
ESTAGIOS_COM_RODADA = {None, "REGULAR_SEASON", "GROUP_STAGE", "LEAGUE_STAGE"}


# Formato fixo das copas conhecidas: a numeração não depende das fases já sorteadas.
FORMATO_COPAS = {
    "CLI": {"rodadas_grupo": 6, "fases": ["Oitavas de final", "Quartas de final", "Semifinal", "Final"]},
    "CS": {"rodadas_grupo": 6, "fases": ["Playoffs", "Oitavas de final", "Quartas de final", "Semifinal", "Final"]},
}


def _rotulos_genericos():
    rotulos = []
    for _, rotulo in FASES_MATA_MATA:
        if rotulo not in rotulos:
            rotulos.append(rotulo)
    return rotulos


def nomes_rodadas_por_estagio(itens, competicao=None, nomes_existentes=()):
    """Função item -> nome local; número inicial mantém a ordem da copa em ordem_rodada.

    A numeração vem do formato da competição (ou das rodadas de grupo já salvas), nunca só
    dos jogos desta resposta: assim um import parcial não põe o mata-mata antes dos grupos
    nem renumera uma fase quando outra aparece depois. Fase já salva é reaproveitada.
    """
    formato = FORMATO_COPAS.get((competicao or "").upper())
    if formato:
        rodadas_grupo, rotulos = formato["rodadas_grupo"], list(formato["fases"])
    else:
        salvas = [int(m.group(1)) for n in nomes_existentes
                  for m in [re.fullmatch(r"Rodada (\d+)", n or "")] if m]
        rodadas_grupo = max([i.get("matchday") or 0 for i in itens
                             if i.get("estagio") in ESTAGIOS_COM_RODADA] + salvas, default=0)
        rotulos = _rotulos_genericos()
    rotulos += [r for r in _rotulos_genericos() if r not in rotulos]
    por_rotulo = {n.split(" · ", 1)[1]: n for n in nomes_existentes if n and " · " in n}

    def nome(item):
        estagio = item.get("estagio")
        if estagio in ESTAGIOS_COM_RODADA:
            return f"Rodada {item['matchday']}" if item.get("matchday") else "Rodada Geral"
        rotulo = dict(FASES_MATA_MATA).get(estagio)
        if rotulo is None:
            return "Rodada 0 · Fase preliminar"
        return por_rotulo.get(rotulo) or f"Rodada {rodadas_grupo + rotulos.index(rotulo) + 1} · {rotulo}"
    return nome


# ---------- API-Football (league.round) ----------

# "8th Finals" = oitavas (8 confrontos), "16th Finals" = 16 avos...
_FINAIS_POR_NUMERO = {32: "LAST_64", 16: "LAST_32", 8: "LAST_16", 4: "QUARTER_FINALS", 2: "SEMI_FINALS"}


def fase_api_football(rodada):
    """league.round -> (estagio, número da rodada na fase, rótulo da fase em português).

    'Group Stage - 3' -> ('GROUP_STAGE', 3, 'Fase de grupos'); '2nd Round' -> ('ROUND_2', None,
    '2ª fase'); 'Round of 16' / '8th Finals' -> ('LAST_16', None, 'Oitavas de final').
    Fases desconhecidas viram ('OUTRA', None, texto original).
    """
    texto = " ".join((rodada or "").split())
    baixo = texto.casefold()
    if not texto:
        return None, None, None
    m = re.fullmatch(r"(regular season|league stage|group stage|group phase|group [a-z])\s*-\s*(\d+)", baixo)
    if m:
        tipo = m.group(1)
        if tipo.startswith("group"):
            return "GROUP_STAGE", int(m.group(2)), "Fase de grupos"
        return ("LEAGUE_STAGE" if tipo == "league stage" else "REGULAR_SEASON"), int(m.group(2)), "Fase de liga"
    m = re.fullmatch(r"(\d+)(?:st|nd|rd|th) round", baixo)
    if m:
        return f"ROUND_{int(m.group(1))}", None, f"{int(m.group(1))}ª fase"
    m = re.fullmatch(r"(\d+)(?:st|nd|rd|th) finals", baixo)
    if m and int(m.group(1)) in _FINAIS_POR_NUMERO:
        estagio = _FINAIS_POR_NUMERO[int(m.group(1))]
        return estagio, None, dict(FASES_MATA_MATA)[estagio]
    if re.fullmatch(r"(preliminary|qualifying|qualification)( round)?( \d+)?", baixo):
        return "PRELIMINARY_ROUND", None, "Fase preliminar"
    if "play-off" in baixo or "playoff" in baixo:
        return "PLAYOFFS", None, "Playoffs"
    fixos = {"round of 64": "LAST_64", "round of 32": "LAST_32", "round of 16": "LAST_16",
             "quarter-finals": "QUARTER_FINALS", "quarter finals": "QUARTER_FINALS",
             "semi-finals": "SEMI_FINALS", "semi finals": "SEMI_FINALS",
             "3rd place final": "THIRD_PLACE", "third place": "THIRD_PLACE", "3rd place": "THIRD_PLACE",
             "final": "FINAL", "finals": "FINAL"}
    if baixo in fixos:
        return fixos[baixo], None, dict(FASES_MATA_MATA)[fixos[baixo]]
    m = re.fullmatch(r".+\s-\s(\d+)", baixo)  # outros formatos de pontos corridos ("1st Phase - 4")
    if m:
        return "REGULAR_SEASON", int(m.group(1)), "Fase de liga"
    return "OUTRA", None, texto


# Formato fixo por liga da API-Football (Campeonato.codigo_api = id da liga). Ordem dos blocos:
# fase preliminar, N fases numeradas ('1st Round'...), M rodadas de grupos/liga, mata-mata.
# Contagens são mínimas: se a resposta (ou o banco) tiver mais, valem as maiores.
FORMATO_API_FOOTBALL = {
    "13": {"preliminar": False, "fases_numeradas": 3, "rodadas": 6,   # Libertadores
           "mata_mata": ["LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]},
    "11": {"preliminar": False, "fases_numeradas": 1, "rodadas": 6,   # Sul-Americana
           "mata_mata": ["PLAYOFFS", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]},
    "73": {"preliminar": False, "fases_numeradas": 3, "rodadas": 0,   # Copa do Brasil
           "mata_mata": ["LAST_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]},
    "629": {"preliminar": False, "fases_numeradas": 0, "rodadas": 8,  # Campeonato Mineiro
            "mata_mata": ["SEMI_FINALS", "FINAL"]},
}
_MATA_MATA_GENERICO = ["PLAYOFFS", "LAST_64", "LAST_32", "LAST_16", "QUARTER_FINALS", "SEMI_FINALS",
                       "THIRD_PLACE", "FINAL"]


def _rotulo_item_api_football(item):
    """Rótulo usado no nome da rodada (depois de ' · ')."""
    estagio, numero = item.get("estagio"), item.get("matchday")
    if estagio in ESTAGIOS_COM_RODADA:
        return f"{item.get('fase') or 'Fase de liga'} - {numero}ª rodada" if numero else None
    return item.get("fase") or dict(FASES_MATA_MATA).get(estagio) or "Fase preliminar"


def nomes_rodadas_api_football(itens, liga=None, nomes_existentes=()):
    """Função item -> nome local para ligas da API-Football, em ordem cronológica.

    Cada fase tem número fixo pelo formato da liga (FORMATO_API_FOOTBALL; demais ligas usam o
    maior entre a resposta e as rodadas já salvas). Ex. Libertadores: 'Rodada 1 · 1ª fase' ...
    'Rodada 4 · Fase de grupos - 1ª rodada' ... 'Rodada 10 · Oitavas de final' ... 'Rodada 13 · Final'.
    Fase já salva (mesmo rótulo) é sempre reaproveitada, sem renumerar nem duplicar.
    """
    formato = FORMATO_API_FOOTBALL.get(str(liga or "").strip()) or {
        "preliminar": False, "fases_numeradas": 0, "rodadas": 0, "mata_mata": []}
    rotulos_salvos = [n.split(" · ", 1)[1] for n in nomes_existentes if n and " · " in n]
    por_rotulo = {n.split(" · ", 1)[1]: n for n in nomes_existentes if n and " · " in n}

    preliminar = formato["preliminar"] or "Fase preliminar" in rotulos_salvos or any(
        i.get("estagio") == "PRELIMINARY_ROUND" for i in itens)
    fases_numeradas = max([formato["fases_numeradas"]]
                          + [int(i["estagio"].split("_")[1]) for i in itens
                             if re.fullmatch(r"ROUND_\d+", i.get("estagio") or "")]
                          + [int(m.group(1)) for r in rotulos_salvos for m in [re.fullmatch(r"(\d+)ª fase", r)] if m])
    antes = int(preliminar) + fases_numeradas
    rodadas = max([formato["rodadas"]]
                  + [i.get("matchday") or 0 for i in itens if i.get("estagio") in ESTAGIOS_COM_RODADA]
                  + [int(m.group(1)) for r in rotulos_salvos for m in [re.search(r" - (\d+)ª rodada$", r)] if m]
                  + ([int(m.group(1)) for n in nomes_existentes for m in [re.fullmatch(r"Rodada (\d+)", n or "")] if m]
                     if antes == 0 else []))
    # Fases fora do formato (não deveria haver) ficam depois das previstas, sem renumerá-las.
    mata_mata = list(formato["mata_mata"]) + [e for e in _MATA_MATA_GENERICO if e not in formato["mata_mata"]]
    rotulos_mata_mata = []
    for estagio in mata_mata:
        rotulo = dict(FASES_MATA_MATA)[estagio]
        if rotulo not in rotulos_mata_mata:
            rotulos_mata_mata.append(rotulo)
    # Fases desconhecidas vão ao fim, na ordem em que aparecem (as já salvas mantêm o nome).
    desconhecidas = []
    for item in sorted(itens, key=lambda i: (i.get("data") is None, i.get("data") or 0, i.get("external_id") or "")):
        if item.get("estagio") == "OUTRA" and item.get("fase") not in desconhecidas:
            desconhecidas.append(item.get("fase"))
    base_fim = antes + rodadas + len(rotulos_mata_mata)
    ocupados = {int(m.group(1)) for n in nomes_existentes for m in [re.match(r"Rodada (\d+)", n or "")] if m}

    def nome(item):
        estagio, rotulo = item.get("estagio"), _rotulo_item_api_football(item)
        if rotulo in por_rotulo:
            return por_rotulo[rotulo]
        if estagio in ESTAGIOS_COM_RODADA:
            numero = item.get("matchday")
            if not numero:
                return "Rodada Geral"
            if antes == 0 and estagio != "GROUP_STAGE":
                return f"Rodada {numero}"
            return f"Rodada {antes + numero} · {rotulo}"
        if estagio == "PRELIMINARY_ROUND":
            return f"Rodada 1 · {rotulo}"
        m = re.fullmatch(r"ROUND_(\d+)", estagio or "")
        if m:
            return f"Rodada {int(preliminar) + int(m.group(1))} · {rotulo}"
        if rotulo in rotulos_mata_mata:
            return f"Rodada {antes + rodadas + rotulos_mata_mata.index(rotulo) + 1} · {rotulo}"
        posicao = desconhecidas.index(rotulo) if rotulo in desconhecidas else 0
        numero = max([base_fim] + [o for o in ocupados if o > base_fim]) + posicao + 1
        return f"Rodada {numero} · {rotulo}"
    return nome


def nomeador_rodadas(fonte_api, itens, competicao=None, nomes_existentes=()):
    if normalizar_fonte(fonte_api) == FONTE_ESPN:
        from services.importador_espn import FORMATO_DA_LIGA
        liga = FORMATO_DA_LIGA.get(competicao, competicao)
        nome_base = nomes_rodadas_api_football(itens, liga, nomes_existentes)
        formato = FORMATO_API_FOOTBALL.get(liga, {})
        antes = formato.get('fases_numeradas', 0) + int(formato.get('preliminar', False))
        por_rotulo = {n.split(' · ', 1)[1]: n for n in nomes_existentes if ' · ' in n}

        def nome_espn(item):
            if item.get('estagio') in ESTAGIOS_COM_RODADA and not item.get('matchday'):
                rotulo = 'Fase de grupos' if item.get('estagio') == 'GROUP_STAGE' else 'Fase de liga'
                return por_rotulo.get(rotulo) or f'Rodada {antes + 1} · {rotulo}'
            return nome_base(item)

        return nome_espn
    if normalizar_fonte(fonte_api) == FONTE_API_FOOTBALL:
        return nomes_rodadas_api_football(itens, competicao, nomes_existentes)
    return nomes_rodadas_por_estagio(itens, competicao, nomes_existentes)


# ---------- Pênaltis ----------

def eh_mata_mata(estagio):
    """Fase eliminatória (copa) em qualquer dos dois provedores; grupos e pontos corridos não."""
    if estagio in ESTAGIOS_COM_RODADA or estagio == "OUTRA":
        return False
    return (estagio in dict(FASES_MATA_MATA) or estagio.startswith(("QUALIFICATION", "PRELIMINARY", "ROUND_")))


def _chave_confronto(item):
    times = frozenset(" ".join((item.get(t) or "").casefold().split()) for t in ("time_casa", "time_fora"))
    return item.get("estagio"), times


def _ordem_jogo(item):
    data = item.get("data")
    return (data is None, data.isoformat() if data else "", str(item.get("external_id") or ""))


def marcar_pode_penaltis(itens, existentes=()):
    """Define item['pode_penaltis']: no mata-mata, jogo único do confronto na fase ou o jogo de
    volta (o posterior dos dois entre o mesmo par na mesma fase). Grupos/pontos corridos: False.

    existentes: jogos já salvos (mesmo formato de dict) que completam um import parcial; não
    são alterados.
    """
    confrontos = {}
    for item in list(existentes) + list(itens):
        if eh_mata_mata(item.get("estagio")):
            confrontos.setdefault(_chave_confronto(item), {})[str(item.get("external_id"))] = item
    for item in itens:
        if not eh_mata_mata(item.get("estagio")):
            item["pode_penaltis"] = False
            continue
        jogos = confrontos[_chave_confronto(item)].values()
        ultimo = max(jogos, key=_ordem_jogo)
        item["pode_penaltis"] = str(ultimo.get("external_id")) == str(item.get("external_id"))
    return itens
