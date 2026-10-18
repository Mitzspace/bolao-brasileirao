"""
sync.py — Sincronização automática de jogos e resultados via football-data.org ou API-Football
(o provedor de cada campeonato vem de Campeonato.fonte_api).

Permite:
  - Importar o campeonato completo (todas as rodadas de 1 a 38 de uma só vez)
  - Importar rodada específica (criando automaticamente o nome conforme a API)
  - Capturar data e hora oficiais (ajustadas para horário de Brasília UTC-3)
  - Puxar e salvar resultados automaticamente de jogos que já aconteceram
  - Atualizar jogos existentes sem duplicar
"""

import os
import sys
import re
import unicodedata


from services.competicoes import (
    ESTAGIOS_COM_RODADA,
    EXTERNAL_FONTE,
    FONTE_API_FOOTBALL, FONTE_ESPN,
    FONTE_FOOTBALL_DATA,
    filtrar_a_partir_da_fase,
    nomeador_rodadas,
    normalizar_fonte,
    ordenador_fases,
)
from services.importador_api_football import (
    buscar_jogos_api_football,
    buscar_resultados_api_football,
)
from services.importador_jogos import (
    buscar_jogos_football_data,
    buscar_resultados_football_data,
)


def chave_api(fonte_api):
    """Chave do servidor para o provedor; ESPN não exige chave (retorna None)."""
    fonte = normalizar_fonte(fonte_api)
    if fonte == FONTE_ESPN:
        return None
    variavel = "API_FOOTBALL_KEY" if fonte == FONTE_API_FOOTBALL else "FOOTBALL_DATA_TOKEN"
    try:
        from flask import current_app
        valor = current_app.config.get(variavel)
    except RuntimeError:  # fora de um app Flask
        valor = None
    return valor or os.environ.get(variavel) or None


def buscar_jogos(fonte_api, chave, competicao, temporada=None, rodada=None, data_inicio=None, data_fim=None):
    """Jogos do provedor no formato interno (uma chamada à API)."""
    if normalizar_fonte(fonte_api) == FONTE_ESPN:
        from services.importador_espn import buscar_jogos_espn
        return buscar_jogos_espn(competicao, temporada, data_inicio=data_inicio, data_fim=data_fim)
    if normalizar_fonte(fonte_api) == FONTE_API_FOOTBALL:
        return buscar_jogos_api_football(chave=chave, liga=competicao, temporada=temporada, rodada=rodada,
                                         data_inicio=data_inicio, data_fim=data_fim)
    return buscar_jogos_football_data(token=chave, competicao=competicao, temporada=temporada, rodada=rodada,
                                      data_inicio=data_inicio, data_fim=data_fim)


def buscar_resultados(fonte_api, chave, competicao, temporada=None, rodada=None, data_inicio=None, data_fim=None):
    if normalizar_fonte(fonte_api) == FONTE_ESPN:
        from services.importador_espn import buscar_resultados_espn
        return buscar_resultados_espn(competicao, temporada, data_inicio=data_inicio, data_fim=data_fim)
    if normalizar_fonte(fonte_api) == FONTE_API_FOOTBALL:
        return buscar_resultados_api_football(chave=chave, liga=competicao, temporada=temporada, rodada=rodada,
                                              data_inicio=data_inicio, data_fim=data_fim)
    return buscar_resultados_football_data(token=chave, competicao=competicao, temporada=temporada,
                                           rodada=rodada, data_inicio=data_inicio, data_fim=data_fim)


def _fonte_do_campeonato(campeonato_id, fonte_api=None):
    if fonte_api:
        return normalizar_fonte(fonte_api)
    from database import db
    from models import Campeonato
    campeonato = db.session.get(Campeonato, campeonato_id) if campeonato_id else None
    return normalizar_fonte(campeonato.fonte_api if campeonato else None)


def _normalizar_texto(valor):
    valor = valor or ""
    sem_acentos = unicodedata.normalize("NFKD", valor)
    sem_acentos = "".join(c for c in sem_acentos if not unicodedata.combining(c))
    valor = sem_acentos.casefold()
    valor = re.sub(r"[^a-z0-9]+", " ", valor)
    valor = re.sub(
        r"\b(futebol clube|football club|clube de regatas|esporte clube|"
        r"sociedade esportiva|associacao atletica|clube atletico|sport club|"
        r"clube do|saf|fc|ec|cr|se|ca|sc|af|fr|fbc)\b",
        " ",
        valor,
    )
    return " ".join(valor.split())


def _normalizar_time(nome):
    nome = _normalizar_texto(nome)
    aliases = {
        "america mineiro": "america mg",
        "america mg": "america mg",
        "athletico paranaense": "athletico pr",
        "athletico pr": "athletico pr",
        "athletico": "athletico pr",
        "atletico paranaense": "athletico pr",
        "paranaense": "athletico pr",
        "atletico mineiro": "atletico mg",
        "atletico mg": "atletico mg",
        "mineiro": "atletico mg",
        "atletico goianiense": "atletico go",
        "atletico go": "atletico go",
        "bragantino": "red bull bragantino",
        "rb bragantino": "red bull bragantino",
        "red bull bragantino": "red bull bragantino",
        "corinthians paulista": "corinthians",
        "corinthians": "corinthians",
        "coritiba fbc": "coritiba",
        "coritiba": "coritiba",
        "chapecoense af": "chapecoense",
        "chapecoense": "chapecoense",
        "gremio fbpa": "gremio",
        "gremio": "gremio",
        "vasco da gama": "vasco",
        "vasco": "vasco",
        "sao paulo": "sao paulo",
        "botafogo fr": "botafogo",
        "botafogo": "botafogo",
        "cruzeiro ec": "cruzeiro",
        "cruzeiro": "cruzeiro",
        "palmeiras": "palmeiras",
        "flamengo": "flamengo",
        "fluminense": "fluminense",
        "internacional": "internacional",
        "santos": "santos",
        "bahia": "bahia",
        "vitoria": "vitoria",
        "mirassol": "mirassol",
        "remo": "remo",
    }
    return aliases.get(nome, nome)


# Nome exibido de cada clube da Série A, igual ao usado nos bolões (a API manda
# "CA Mineiro", "SC Corinthians Paulista", "CR Vasco da Gama"...). Chave: _normalizar_time.
NOMES_PADRAO = {
    "athletico pr": "Athletico-PR", "atletico mg": "Atlético-MG", "bahia": "Bahia",
    "botafogo": "Botafogo", "chapecoense": "Chapecoense", "corinthians": "Corinthians",
    "coritiba": "Coritiba", "cruzeiro": "Cruzeiro", "flamengo": "Flamengo",
    "fluminense": "Fluminense", "gremio": "Grêmio", "internacional": "Internacional",
    "mirassol": "Mirassol", "palmeiras": "Palmeiras", "red bull bragantino": "Red Bull Bragantino",
    "remo": "Remo", "santos": "Santos", "sao paulo": "São Paulo", "vasco": "Vasco",
    "vitoria": "Vitória",
}


def nome_padrao(nome):
    """Nome curto e único do clube; times fora da lista (outros campeonatos) ficam como vieram."""
    return NOMES_PADRAO.get(_normalizar_time(nome), nome)


def _matchday_da_rodada(rodada):
    match = re.search(r"\d+", rodada.nome or "")
    return int(match.group()) if match else None


def _chave_jogo(time_casa, time_fora):
    return (_normalizar_time(time_casa), _normalizar_time(time_fora))


def _gravar_resultado(db, Resultado, jogo, item):
    """Placar do jogo normal (+ pênaltis, quando houver) e encerra o jogo."""
    resultado = Resultado.query.filter_by(jogo_id=jogo.id).first()
    if resultado is None:
        resultado = Resultado(jogo_id=jogo.id)
        db.session.add(resultado)
    resultado.gols_casa_real = item["gols_casa_real"]
    resultado.gols_fora_real = item["gols_fora_real"]
    if item.get("penaltis_casa_real") is not None and item.get("penaltis_fora_real") is not None:
        resultado.penaltis_casa_real = item["penaltis_casa_real"]
        resultado.penaltis_fora_real = item["penaltis_fora_real"]
    jogo.encerrado = True


def _salvar_resultado_se_finalizado(db, Resultado, jogo, item):
    if not item["finalizado"] or item["gols_casa_real"] is None or item["gols_fora_real"] is None:
        return False
    _gravar_resultado(db, Resultado, jogo, item)
    return True


def _ordem_cronologica(data, external_id):
    return (data is None, data.isoformat() if data else "", str(external_id or ""))


def _pode_penaltis(item, rodada):
    """pode_penaltis da API, corrigido pelos jogos já salvos na mesma rodada: num import parcial
    a ida sozinha parece jogo único; se a volta (posterior, mesmo par) já está no banco, não é."""
    if not item.get("pode_penaltis"):
        return False
    par = frozenset(_chave_jogo(item["time_casa"], item["time_fora"]))
    ordem = _ordem_cronologica(item.get("data"), item["external_id"])
    return not any(
        outro.external_id != item["external_id"]
        and frozenset(_chave_jogo(outro.time_casa, outro.time_fora)) == par
        and _ordem_cronologica(outro.data, outro.external_id) > ordem
        for outro in rodada.jogos)


def _aplicar_pode_penaltis(jogo, item, rodada):
    # A sincronização só liga a opção: nunca desfaz o que o responsável marcou à mão.
    if rodada is not None and _pode_penaltis(item, rodada):
        jogo.pode_penaltis = True


def _numero_da_rodada(nome):
    match = re.search(r"\d+", nome or "")
    return int(match.group()) if match else None


def sync_jogos(token, campeonato_id, competicao,
               nome_rodada=None, temporada=None, rodada_api=None,
               data_inicio=None, data_fim=None, campeonato_completo=False, jogos_api=None, fonte_api=None,
               fase_inicial=None):
    """
    Importa jogos da API e salva no banco de dados.
    - fase_inicial: estágio (ex.: 'LAST_32' = 16 avos) a partir do qual importar; None = todas as fases.
    - Se campeonato_completo=True: importa todas as rodadas e cria cada uma conforme o matchday da API.
    - Se campeonato_completo=False: importa a rodada informada (ou rodada_api).
    - Salva data/hora em horário de Brasília.
    - Se a partida já aconteceu, salva o resultado real (e os pênaltis) e marca encerrado = True.
    - jogos_api: lista já buscada (ex.: compartilhada entre bolões); se vier, não chama a API.
    - fonte_api: provedor ('football-data' | 'api-football'); padrão = o do campeonato.
      Na API-Football, rodada_api é o número da rodada local (ex.: 10 = Oitavas na Libertadores).
    """
    from database import db
    from models import Jogo, Resultado, Rodada
    from services.classicos import eh_classico

    fonte = _fonte_do_campeonato(campeonato_id, fonte_api)
    rodada_local = fonte in (FONTE_API_FOOTBALL, FONTE_ESPN)
    external_fonte = EXTERNAL_FONTE[fonte]

    # Se for campeonato completo, não filtra por rodada na chamada da API
    filtro_rodada = None if campeonato_completo else rodada_api

    if jogos_api is None:
        jogos_api = buscar_jogos(
            fonte, token, competicao,
            temporada=temporada,
            rodada=None if rodada_local else filtro_rodada,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    jogos_api = filtrar_a_partir_da_fase(jogos_api, fase_inicial, competicao)

    criados = 0
    atualizados = 0
    resultados_salvos = 0
    rodadas_criadas = 0

    # Cache de rodadas existentes no campeonato para evitar queries repetidas
    rodadas_db = {r.nome: r for r in Rodada.query.filter_by(campeonato_id=campeonato_id).all()}
    nome_por_estagio = nomeador_rodadas(fonte, jogos_api, competicao, list(rodadas_db))
    if rodada_local and filtro_rodada and str(filtro_rodada).isdigit():
        jogos_api = [i for i in jogos_api if _numero_da_rodada(nome_por_estagio(i)) == int(filtro_rodada)]

    for item in jogos_api:
        # Determina o nome da rodada; em copas, o mata-mata é nomeado pela fase.
        mata_mata = item.get("estagio") not in ESTAGIOS_COM_RODADA
        if campeonato_completo:
            nome_rod = nome_por_estagio(item)
        elif rodada_local:
            nome_rod = (nome_rodada or "").strip() or nome_por_estagio(item)
        else:
            if nome_rodada and nome_rodada.strip():
                nome_rod = nome_rodada.strip()
            elif mata_mata:
                nome_rod = nome_por_estagio(item)
            elif item.get("matchday"):
                nome_rod = f"Rodada {item['matchday']}"
            else:
                nome_rod = "Rodada Importada"

        # Localiza ou cria a rodada
        rodada = rodadas_db.get(nome_rod)
        if not rodada:
            rodada = Rodada(nome=nome_rod, campeonato_id=campeonato_id, aberta=True)
            db.session.add(rodada)
            db.session.flush() # obtém rodada.id
            rodadas_db[nome_rod] = rodada
            rodadas_criadas += 1

        # Verifica se o jogo já existe neste campeonato (cada bolão tem o seu campeonato:
        # dois bolões do mesmo torneio não podem "roubar" os jogos um do outro).
        jogo = Jogo.query.join(Rodada, Rodada.id == Jogo.rodada_id).filter(
            Rodada.campeonato_id == campeonato_id,
            Jogo.external_fonte == external_fonte,
            Jogo.external_id == item["external_id"],
        ).first()

        if jogo is None:
            jogo = Jogo(
                time_casa=nome_padrao(item["time_casa"]),
                time_fora=nome_padrao(item["time_fora"]),
                data=item["data"],
                rodada_id=rodada.id,
                especial=eh_classico(item["time_casa"], item["time_fora"]),
                encerrado=item["finalizado"],
                pode_penaltis=_pode_penaltis(item, rodada),
                external_fonte=external_fonte,
                external_id=item["external_id"],
            )
            db.session.add(jogo)
            db.session.flush()
            criados += 1
        else:
            # Atualiza informações que podem ter mudado (ex: data, times)
            jogo.time_casa = nome_padrao(item["time_casa"])
            jogo.time_fora = nome_padrao(item["time_fora"])
            if item["data"]:
                jogo.data = item["data"]
            if item["finalizado"]:
                jogo.encerrado = True
            _aplicar_pode_penaltis(jogo, item, jogo.rodada or rodada)
            atualizados += 1

        # Se o jogo já aconteceu / tem placar real, salva o Resultado
        if _salvar_resultado_se_finalizado(db, Resultado, jogo, item):
            resultados_salvos += 1

    db.session.commit()

    return {
        "criados": criados,
        "atualizados": atualizados,
        "resultados_salvos": resultados_salvos,
        "rodadas_criadas": rodadas_criadas,
        "total_jogos_api": len(jogos_api),
    }


def sync_resultados(token, competicao,
                    temporada=None, rodada_api=None, data_inicio=None, data_fim=None, fonte_api=None):
    """
    Busca resultados finalizados na API e atualiza os jogos locais do mesmo provedor.
    Marca os jogos como encerrados automaticamente.
    """
    from database import db
    from models import Jogo, Resultado

    fonte = normalizar_fonte(fonte_api)
    resultados_api = buscar_resultados(
        fonte, token, competicao, temporada=temporada,
        rodada=None if fonte == FONTE_API_FOOTBALL else rodada_api,
        data_inicio=data_inicio, data_fim=data_fim,
    )

    atualizados = 0
    ignorados = 0

    for item in resultados_api:
        # Cada bolão tem a sua cópia do jogo (mesmo external_id): o resultado vale para todas.
        consulta = Jogo.query.filter_by(
            external_fonte=EXTERNAL_FONTE[fonte],
            external_id=item["external_id"],
        )
        jogos = consulta.all()
        if fonte in (FONTE_API_FOOTBALL, FONTE_ESPN) and rodada_api:
            jogos = [j for j in jogos if _matchday_da_rodada(j.rodada) == int(rodada_api)]

        if not jogos:
            ignorados += 1
            continue

        for jogo in jogos:
            _gravar_resultado(db, Resultado, jogo, item)
            atualizados += 1

    db.session.commit()
    return {"atualizados": atualizados, "ignorados": ignorados, "total_api": len(resultados_api)}


def sync_informacoes_jogos(token, campeonato_id, competicao,
                           temporada=None, data_inicio=None, data_fim=None,
                           salvar_resultados=True, jogos_api=None, fonte_api=None):
    """
    Atualiza jogos locais já cadastrados com dados oficiais da API.
    Não cria jogos novos. Usa external_id quando disponível e, para jogos
    importados de planilha, tenta casar por rodada/matchday e mandante/visitante.
    salvar_resultados=False atualiza somente horários (e o vínculo com a API),
    sem encerrar jogos nem gravar placares.
    jogos_api: lista já buscada (ex.: compartilhada entre bolões); se vier, não chama a API.
    fonte_api: provedor; padrão = o do campeonato.
    """
    from database import db
    from models import Resultado, Rodada

    fonte = _fonte_do_campeonato(campeonato_id, fonte_api)
    external_fonte = EXTERNAL_FONTE[fonte]
    if jogos_api is None:
        jogos_api = buscar_jogos(
            fonte, token, competicao,
            temporada=temporada,
            rodada=None,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    rodadas = Rodada.query.filter_by(campeonato_id=campeonato_id).all()
    # Na API-Football o número que casa com a rodada local vem do nome (Rodada 10 · Oitavas...).
    nome_por_estagio = (nomeador_rodadas(fonte, jogos_api, competicao, [r.nome for r in rodadas])
                        if fonte in (FONTE_API_FOOTBALL, FONTE_ESPN) else None)
    rodadas_por_matchday = {
        matchday: rodada
        for rodada in rodadas
        for matchday in [_matchday_da_rodada(rodada)]
        if matchday is not None
    }

    jogos_por_external_id = {
        jogo.external_id: jogo
        for rodada in rodadas
        for jogo in rodada.jogos
        if jogo.external_fonte == external_fonte and jogo.external_id
    }

    jogos_por_rodada_e_times = {}
    for rodada in rodadas:
        matchday = _matchday_da_rodada(rodada)
        if matchday is None:
            continue

        for jogo in rodada.jogos:
            jogos_por_rodada_e_times[(matchday, _chave_jogo(jogo.time_casa, jogo.time_fora))] = jogo

    atualizados = 0
    horarios_atualizados = 0
    resultados_salvos = 0
    ignorados = 0

    for item in jogos_api:
        jogo = jogos_por_external_id.get(item["external_id"])

        if jogo is None:
            matchday = (_numero_da_rodada(nome_por_estagio(item)) if nome_por_estagio
                        else item.get("matchday"))
            jogo = jogos_por_rodada_e_times.get(
                (matchday, _chave_jogo(item["time_casa"], item["time_fora"]))
            )

        if jogo is None:
            ignorados += 1
            continue

        data_anterior = jogo.data

        jogo.external_fonte = external_fonte
        jogo.external_id = item["external_id"]
        _aplicar_pode_penaltis(jogo, item, jogo.rodada)

        if item["data"]:
            jogo.data = item["data"]
            if data_anterior != jogo.data:
                horarios_atualizados += 1

        if salvar_resultados:
            if item["finalizado"]:
                jogo.encerrado = True

            if _salvar_resultado_se_finalizado(db, Resultado, jogo, item):
                resultados_salvos += 1

        atualizados += 1

    db.session.commit()

    return {
        "atualizados": atualizados,
        "horarios_atualizados": horarios_atualizados,
        "resultados_salvos": resultados_salvos,
        "ignorados": ignorados,
        "total_api": len(jogos_api),
    }


def campeonatos_da_competicao(competicao, temporada, fonte_api=None, incluir_sem_rodadas=False):
    """Campeonatos (um por bolão) do mesmo provedor, competição e temporada que já têm rodadas
    (incluir_sem_rodadas=True também traz os ainda vazios)."""
    from models import Campeonato
    from sqlalchemy import func
    fonte = normalizar_fonte(fonte_api)
    return [c for c in Campeonato.query.filter(
                func.upper(func.trim(Campeonato.codigo_api)) == (competicao or "").strip().upper(),
                Campeonato.ano == temporada,
                func.coalesce(Campeonato.fonte_api, FONTE_FOOTBALL_DATA) == fonte).all()
            if incluir_sem_rodadas or c.rodadas]


def importar_jogos_novos(token, campeonato_id, competicao, temporada, jogos_api, fonte_api):
    """Cria só os jogos da resposta que o campeonato ainda não tem (ex.: fase recém-sorteada).

    Os já cadastrados ficam fora para não criar rodadas vazias quando o nome calculado hoje
    difere do salvo; horários e resultados deles são atualizados por sync_informacoes_jogos.
    """
    from models import Jogo, Rodada
    fonte = normalizar_fonte(fonte_api)
    existentes = {j.external_id for j in Jogo.query.join(Rodada, Rodada.id == Jogo.rodada_id).filter(
        Rodada.campeonato_id == campeonato_id, Jogo.external_fonte == EXTERNAL_FONTE[fonte])}
    novos = [i for i in jogos_api if i["external_id"] not in existentes]
    # Respeita a fase inicial escolhida na importação: fases anteriores à mais antiga já
    # cadastrada (ex.: 1ª a 2ª fase da Copa do Brasil, importada só dos 16 avos) não voltam.
    ordem = ordenador_fases(jogos_api, competicao)
    ordens = [o for i in jogos_api if i["external_id"] in existentes
              for o in [ordem(i.get("estagio"))] if o is not None]
    if ordens:
        novos = [i for i in novos if ordem(i.get("estagio")) is None or ordem(i.get("estagio")) >= min(ordens)]
    if not novos:
        return {"criados": 0, "rodadas_criadas": 0}
    r = sync_jogos(token, campeonato_id, competicao, temporada=temporada, campeonato_completo=True,
                   jogos_api=novos, fonte_api=fonte)
    return {"criados": r["criados"], "rodadas_criadas": r["rodadas_criadas"]}


def sync_competicao(token, competicao, temporada, data_inicio=None, data_fim=None, fonte_api=None):
    """Uma chamada à API por (provedor, competição, temporada), aplicada a todos os campeonatos dela.

    A falha num campeonato é registrada e não impede os demais.
    """
    import logging
    from database import db

    fonte = normalizar_fonte(fonte_api)
    jogos_api = buscar_jogos(fonte, token, competicao, temporada=temporada,
                             data_inicio=data_inicio, data_fim=data_fim)
    resultados = {}
    # ESPN é gratuita e não informa fases futuras antes do sorteio: o worker também cria os
    # jogos novos (inclusive em campeonato ainda vazio, se a importação na criação falhou).
    cria_jogos = fonte == FONTE_ESPN
    for campeonato_id in [c.id for c in campeonatos_da_competicao(competicao, temporada, fonte,
                                                                   incluir_sem_rodadas=cria_jogos)]:
        try:
            novos = (importar_jogos_novos(token, campeonato_id, competicao, temporada, jogos_api, fonte)
                     if cria_jogos else None)
            resultados[campeonato_id] = sync_informacoes_jogos(
                token, campeonato_id, competicao, temporada=temporada, jogos_api=jogos_api,
                fonte_api=fonte)
            if novos:
                resultados[campeonato_id] = {**resultados[campeonato_id], "criados": novos["criados"],
                                             "rodadas_criadas": novos["rodadas_criadas"]}
        except Exception:
            db.session.rollback()
            logging.getLogger(__name__).exception(
                "Falha ao aplicar %s/%s/%s no campeonato %s", fonte, competicao, temporada, campeonato_id)
    return resultados


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync bolão — football-data.org / API-Football / ESPN")
    parser.add_argument("acao", choices=["jogos", "resultados"], help="Ação a executar")
    parser.add_argument("--competicao", required=True, help="Código da competição (ex: BSA)")
    parser.add_argument("--campeonato-id", type=int, default=None, help="ID do campeonato local")
    parser.add_argument("--completo", action="store_true", help="Importar campeonato por completo")
    parser.add_argument("--rodada", default=None, help="Número da rodada na API")
    parser.add_argument("--nome-rodada", default=None, help="Nome da rodada local")
    parser.add_argument("--temporada", default=None, help="Ano da temporada (ex: 2025)")
    parser.add_argument("--fonte", choices=[FONTE_FOOTBALL_DATA, FONTE_API_FOOTBALL, FONTE_ESPN], default=None,
                        help="Provedor (padrão: o do campeonato; sem campeonato, football-data)")

    args = parser.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import create_app
    app = create_app()

    with app.app_context():
        fonte = _fonte_do_campeonato(args.campeonato_id, args.fonte)
        token = chave_api(fonte)
        if fonte != FONTE_ESPN and not token:
            variavel = "API_FOOTBALL_KEY" if fonte == FONTE_API_FOOTBALL else "FOOTBALL_DATA_TOKEN"
            parser.error(f"Defina {variavel}.")
        if args.acao == "jogos":
            res = sync_jogos(
                token=token,
                campeonato_id=args.campeonato_id,
                competicao=args.competicao,
                nome_rodada=args.nome_rodada,
                temporada=args.temporada,
                rodada_api=args.rodada,
                campeonato_completo=args.completo,
                fonte_api=fonte,
            )
            print(f"Resultado: {res}")
        elif args.acao == "resultados":
            res = sync_resultados(
                token=token,
                competicao=args.competicao,
                temporada=args.temporada,
                rodada_api=args.rodada,
                fonte_api=fonte,
            )
            print(f"Resultado: {res}")
