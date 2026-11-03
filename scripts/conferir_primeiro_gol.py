"""Confere os bônus de primeiro gol já disputados e preenche os marcadores pela ESPN.

Uso (na pasta do projeto, com o .env de produção):
    python -m scripts.conferir_primeiro_gol                 # simulação: só relatório, nada é gravado
    python -m scripts.conferir_primeiro_gol --bolao 3       # um bolão
    python -m scripts.conferir_primeiro_gol --aplicar       # grava (pede confirmação)

Opções: --liga-espn SLUG força a liga da ESPN (ex.: bra.1); --saida PASTA define onde salvar os CSVs.
Faça um backup do banco antes de usar --aplicar. Explicação das situações em
services/conferencia_primeiro_gol.py e docs/PRIMEIRO_GOL.md.
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


def _nome_jogo(jogo):
    return f"{jogo.time_casa} {jogo.resultado.gols_casa_real} x {jogo.resultado.gols_fora_real} {jogo.time_fora}"


def _salvar_csv(pasta, nome, cabecalho, linhas):
    caminho = pasta / nome
    with caminho.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
    return caminho


def salvar_relatorio(relatorio, pasta):
    from services.conferencia_primeiro_gol import DESCRICAO_JOGO, DESCRICAO_PESSOA
    prefixo = f"bolao{relatorio.bolao.id}"
    _salvar_csv(pasta, f"{prefixo}-jogos.csv",
                ["rodada", "jogo", "data", "marcador_atual", "marcador_espn", "situacao"],
                [[l["jogo"].rodada.nome, _nome_jogo(l["jogo"]),
                  l["jogo"].data.strftime("%d/%m/%Y %H:%M") if l["jogo"].data else "",
                  l["marcador_atual"] or "", l["marcador_espn"] or "", DESCRICAO_JOGO[l["situacao"]]]
                 for l in relatorio.jogos])
    _salvar_csv(pasta, f"{prefixo}-pessoas.csv",
                ["rodada", "participante", "credito_planilha", "bonus_calculado_hoje", "bonus_recalculado",
                 "credito_depois", "variacao_pontos", "situacao", "credito_nao_multiplo", "jogos_acertados"],
                [[l["rodada"].nome, l["participacao"].nome_exibicao, l["credito"], l["bonus_atual"],
                  l["bonus_novo"], l["credito_novo"], l["variacao"], DESCRICAO_PESSOA[l["situacao"]],
                  "sim" if l["nao_multiplo"] else "", " | ".join(l["acertos"])]
                 for l in relatorio.pessoas])
    _salvar_csv(pasta, f"{prefixo}-quase-acertos.csv",
                ["rodada", "participante", "jogo", "palpite", "marcador_oficial"],
                [[q["jogo"].rodada.nome, q["participacao"].nome_exibicao, _nome_jogo(q["jogo"]),
                  q["palpite"], q["oficial"]] for q in relatorio.quase])


def imprimir_resumo(relatorio):
    from services.conferencia_primeiro_gol import DESCRICAO_JOGO, DESCRICAO_PESSOA
    print(f"\n=== Bolão {relatorio.bolao.id}: {relatorio.bolao.nome} ===")
    print(f"Jogos especiais encerrados: {len(relatorio.jogos)}")
    for situacao, total in Counter(l["situacao"] for l in relatorio.jogos).most_common():
        print(f"  {DESCRICAO_JOGO[situacao]}: {total}")
    for linha in relatorio.jogos:
        if linha["situacao"] in ("digitado_diferente", "placar_diferente", "nao_encontrado"):
            print(f"    {linha['jogo'].rodada.nome} · {_nome_jogo(linha['jogo'])}: "
                  f"digitado {linha['marcador_atual'] or '-'} | ESPN {linha['marcador_espn'] or '-'} "
                  f"({DESCRICAO_JOGO[linha['situacao']]})")
    print("Participações x rodadas:")
    for situacao, total in Counter(l["situacao"] for l in relatorio.pessoas).most_common():
        print(f"  {DESCRICAO_PESSOA[situacao]}: {total}")
    variacao = Counter()
    for linha in relatorio.pessoas:
        variacao[linha["participacao"].nome_exibicao] += linha["variacao"]
    mudancas = [(nome, v) for nome, v in variacao.items() if v]
    if mudancas:
        print("Variação de pontos no total, se aplicar:")
        for nome, v in sorted(mudancas, key=lambda i: (-abs(i[1]), i[0])):
            print(f"  {nome}: {v:+d}")
    else:
        print("Nenhum total de pontos muda.")
    print(f"Palpites quase certos para revisar: {len(relatorio.quase)}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bolao", type=int, action="append", help="id do bolão (repita para vários)")
    parser.add_argument("--liga-espn", help="liga da ESPN, quando o campeonato não tem correspondência")
    parser.add_argument("--aplicar", action="store_true", help="grava marcadores e ajusta créditos")
    parser.add_argument("--sim", action="store_true", help="não pergunta antes de aplicar")
    parser.add_argument("--saida", type=Path, help="pasta dos relatórios CSV")
    args = parser.parse_args(argv)

    from app import create_app
    from database import db
    from models import Bolao
    from services.conferencia_primeiro_gol import aplicar, conferir, eventos_para_conferencia
    from services.primeiro_gol import liga_espn
    from services.relogio import agora_brasilia

    app = create_app()
    with app.app_context():
        agora = agora_brasilia()
        pasta = args.saida or Path.home() / f"conferencia-primeiro-gol-{agora:%Y%m%d-%H%M}"
        pasta.mkdir(parents=True, exist_ok=True)
        boloes = Bolao.query.filter(Bolao.id.in_(args.bolao)).all() if args.bolao else Bolao.query.all()
        relatorios, eventos_por_campeonato = [], {}
        for bolao in sorted(boloes, key=lambda b: b.id):
            campeonato = bolao.campeonato
            liga = args.liga_espn or liga_espn(campeonato)
            if not liga:
                print(f"Bolão {bolao.id} ({bolao.nome}): campeonato sem liga da ESPN conhecida; "
                      "use --liga-espn. Ignorado.")
                continue
            if campeonato.id not in eventos_por_campeonato:
                eventos_por_campeonato[campeonato.id] = eventos_para_conferencia(campeonato, liga)
            relatorio = conferir(bolao, eventos_por_campeonato[campeonato.id])
            if not relatorio.jogos and not relatorio.pessoas:
                continue
            salvar_relatorio(relatorio, pasta)
            imprimir_resumo(relatorio)
            relatorios.append(relatorio)
        print(f"\nRelatórios CSV em: {pasta}")

        if not args.aplicar:
            print("Simulação: nada foi gravado. Revise os CSVs e rode de novo com --aplicar.")
            return 0
        if not args.sim and input("Gravar marcadores e ajustar créditos? Digite 'sim': ").strip().lower() != "sim":
            print("Cancelado: nada foi gravado.")
            return 1
        totais = [0, 0, 0]
        for relatorio in relatorios:
            totais = [t + n for t, n in zip(totais, aplicar(relatorio, f"{agora:%d/%m/%Y}"))]
        db.session.commit()
        print(f"Gravado: {totais[0]} marcadores preenchidos, {totais[1]} palpites de 1º gol registrados, "
              f"{totais[2]} créditos ajustados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
