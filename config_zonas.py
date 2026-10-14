"""
config_zonas.py — Configuração de zonas e destaques na tabela por competição.
"""

ZONAS_COMPETICAO = {
    "BSA": {
        "nome": "Brasileirão Série A",
        "tipo": "tabela_unica",
        "zonas": [
            {
                "faixa": (1, 4),
                "cor": "#4ade80",
                "nome": "Fase de Grupos Libertadores",
            },
            {
                "faixa": (5, 6),
                "cor": "#60a5fa",
                "nome": "Pré-Libertadores",
            },
            {
                "faixa": (7, 12),
                "cor": "#fbbf24",
                "nome": "Copa Sul-Americana",
            },
            {
                "faixa": (17, 20),
                "cor": "#f87171",
                "nome": "Rebaixamento",
            },
        ],
    },
    "CL": {
        "nome": "UEFA Champions League",
        "tipo": "fase_liga",
        "zonas": [
            {
                "faixa": (1, 8),
                "cor": "#4ade80",
                "nome": "Oitavas de Final (Direto)",
            },
            {
                "faixa": (9, 24),
                "cor": "#fbbf24",
                "nome": "Playoffs (16 avos)",
            },
            {
                "faixa": (25, 36),
                "cor": "#f87171",
                "nome": "Eliminados",
            },
        ],
    },
}


def obter_zona(competicao_codigo, posicao, estagio=None):
    """Retorna as informações de estilo/zona para uma dada posição."""
    conf = ZONAS_COMPETICAO.get(competicao_codigo.upper()) if competicao_codigo else None
    if not conf:
        return None
    if estagio == "GROUP_STAGE" and conf.get("tipo") == "fase_liga":
        return None

    for z in conf.get("zonas", []):
        if z.get("estagios") and estagio not in z["estagios"]:
            continue
        min_p, max_p = z["faixa"]
        if min_p <= posicao <= max_p:
            return z
    return None


def obter_legendas(competicao_codigo, estagios=None):
    """Retorna lista de zonas para renderizar a legenda da tabela."""
    conf = ZONAS_COMPETICAO.get(competicao_codigo.upper()) if competicao_codigo else None
    if not conf:
        return []
    if estagios is not None:
        if not estagios or (conf.get("tipo") == "fase_liga" and all(e == "GROUP_STAGE" for e in estagios)):
            return []
        return [z for z in conf.get("zonas", [])
                if not z.get("estagios") or any(e in z["estagios"] for e in estagios)]
    return conf.get("zonas", [])
