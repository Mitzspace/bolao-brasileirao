"""
sync.py — Sincronização automática de jogos e resultados via football-data.org.

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


from services.importador_jogos import (
    buscar_jogos_football_data,
    buscar_resultados_football_data,
)


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


def _matchday_da_rodada(rodada):
    match = re.search(r"\d+", rodada.nome or "")
    return int(match.group()) if match else None


def _chave_jogo(time_casa, time_fora):
    return (_normalizar_time(time_casa), _normalizar_time(time_fora))


def _salvar_resultado_se_finalizado(db, Resultado, jogo, item):
    if not item["finalizado"] or item["gols_casa_real"] is None or item["gols_fora_real"] is None:
        return False

    resultado = Resultado.query.filter_by(jogo_id=jogo.id).first()
    if resultado is None:
        resultado = Resultado(jogo_id=jogo.id)
        db.session.add(resultado)

    resultado.gols_casa_real = item["gols_casa_real"]
    resultado.gols_fora_real = item["gols_fora_real"]
    jogo.encerrado = True
    return True


def sync_jogos(token, campeonato_id, competicao,
               nome_rodada=None, temporada=None, rodada_api=None,
               data_inicio=None, data_fim=None, campeonato_completo=False):
    """
    Importa jogos da API e salva no banco de dados.
    - Se campeonato_completo=True: importa todas as rodadas e cria cada uma conforme o matchday da API.
    - Se campeonato_completo=False: importa a rodada informada (ou rodada_api).
    - Salva data/hora em horário de Brasília.
    - Se a partida já aconteceu, salva o resultado real e marca encerrado = True.
    """
    from database import db
    from models import Jogo, Resultado, Rodada

    # Se for campeonato completo, não filtra por rodada na chamada da API
    filtro_rodada = None if campeonato_completo else rodada_api

    jogos_api = buscar_jogos_football_data(
        token=token,
        competicao=competicao,
        temporada=temporada,
        rodada=filtro_rodada,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    criados = 0
    atualizados = 0
    resultados_salvos = 0
    rodadas_criadas = 0

    # Cache de rodadas existentes no campeonato para evitar queries repetidas
    rodadas_db = {r.nome: r for r in Rodada.query.filter_by(campeonato_id=campeonato_id).all()}

    for item in jogos_api:
        # Determina o nome da rodada
        if campeonato_completo:
            matchday = item.get("matchday")
            nome_rod = f"Rodada {matchday}" if matchday else "Rodada Geral"
        else:
            if nome_rodada and nome_rodada.strip():
                nome_rod = nome_rodada.strip()
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
            Jogo.external_fonte == "football-data.org",
            Jogo.external_id == item["external_id"],
        ).first()

        novo_jogo = False
        if jogo is None:
            jogo = Jogo(
                time_casa=item["time_casa"],
                time_fora=item["time_fora"],
                data=item["data"],
                rodada_id=rodada.id,
                especial=False,
                encerrado=item["finalizado"],
                external_fonte="football-data.org",
                external_id=item["external_id"],
            )
            db.session.add(jogo)
            db.session.flush()
            criados += 1
            novo_jogo = True
        else:
            # Atualiza informações que podem ter mudado (ex: data, times)
            jogo.time_casa = item["time_casa"]
            jogo.time_fora = item["time_fora"]
            if item["data"]:
                jogo.data = item["data"]
            if item["finalizado"]:
                jogo.encerrado = True
            atualizados += 1

        # Se o jogo já aconteceu / tem placar real, salva o Resultado
        if item["finalizado"] and item["gols_casa_real"] is not None and item["gols_fora_real"] is not None:
            resultado = Resultado.query.filter_by(jogo_id=jogo.id).first()
            if resultado is None:
                resultado = Resultado(jogo_id=jogo.id)
                db.session.add(resultado)
            resultado.gols_casa_real = item["gols_casa_real"]
            resultado.gols_fora_real = item["gols_fora_real"]
            jogo.encerrado = True
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
                    temporada=None, rodada_api=None, data_inicio=None, data_fim=None):
    """
    Busca resultados finalizados na API e atualiza os jogos locais.
    Marca os jogos como encerrados automaticamente.
    """
    from database import db
    from models import Jogo, Resultado

    resultados_api = buscar_resultados_football_data(
        token=token, competicao=competicao, temporada=temporada,
        rodada=rodada_api, data_inicio=data_inicio, data_fim=data_fim,
    )

    atualizados = 0
    ignorados = 0

    for item in resultados_api:
        jogo = Jogo.query.filter_by(
            external_fonte="football-data.org",
            external_id=item["external_id"],
        ).first()

        if jogo is None:
            ignorados += 1
            continue

        resultado = Resultado.query.filter_by(jogo_id=jogo.id).first()
        if resultado is None:
            resultado = Resultado(jogo_id=jogo.id)
            db.session.add(resultado)

        resultado.gols_casa_real = item["gols_casa_real"]
        resultado.gols_fora_real = item["gols_fora_real"]
        jogo.encerrado = True
        atualizados += 1

    db.session.commit()
    return {"atualizados": atualizados, "ignorados": ignorados, "total_api": len(resultados_api)}


def sync_informacoes_jogos(token, campeonato_id, competicao,
                           temporada=None, data_inicio=None, data_fim=None,
                           salvar_resultados=True):
    """
    Atualiza jogos locais já cadastrados com dados oficiais da API.
    Não cria jogos novos. Usa external_id quando disponível e, para jogos
    importados de planilha, tenta casar por rodada/matchday e mandante/visitante.
    salvar_resultados=False atualiza somente horários (e o vínculo com a API),
    sem encerrar jogos nem gravar placares.
    """
    from database import db
    from models import Jogo, Resultado, Rodada

    jogos_api = buscar_jogos_football_data(
        token=token,
        competicao=competicao,
        temporada=temporada,
        rodada=None,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    rodadas = Rodada.query.filter_by(campeonato_id=campeonato_id).all()
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
        if jogo.external_fonte == "football-data.org" and jogo.external_id
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
            matchday = item.get("matchday")
            jogo = jogos_por_rodada_e_times.get(
                (matchday, _chave_jogo(item["time_casa"], item["time_fora"]))
            )

        if jogo is None:
            ignorados += 1
            continue

        data_anterior = jogo.data

        jogo.external_fonte = "football-data.org"
        jogo.external_id = item["external_id"]

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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync bolão — football-data.org")
    parser.add_argument("acao", choices=["jogos", "resultados"], help="Ação a executar")
    parser.add_argument("--competicao", required=True, help="Código da competição (ex: BSA)")
    parser.add_argument("--campeonato-id", type=int, default=None, help="ID do campeonato local")
    parser.add_argument("--completo", action="store_true", help="Importar campeonato por completo")
    parser.add_argument("--rodada", default=None, help="Número da rodada na API")
    parser.add_argument("--nome-rodada", default=None, help="Nome da rodada local")
    parser.add_argument("--temporada", default=None, help="Ano da temporada (ex: 2025)")

    args = parser.parse_args()
    token = os.environ.get("FOOTBALL_DATA_TOKEN")
    if not token:
        print("Defina FOOTBALL_DATA_TOKEN.")
        sys.exit(1)

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import create_app
    app = create_app()

    with app.app_context():
        if args.acao == "jogos":
            res = sync_jogos(
                token=token,
                campeonato_id=args.campeonato_id,
                competicao=args.competicao,
                nome_rodada=args.nome_rodada,
                temporada=args.temporada,
                rodada_api=args.rodada,
                campeonato_completo=args.completo,
            )
            print(f"Resultado: {res}")
        elif args.acao == "resultados":
            res = sync_resultados(
                token=token,
                competicao=args.competicao,
                temporada=args.temporada,
                rodada_api=args.rodada,
            )
            print(f"Resultado: {res}")
