#!/usr/bin/env python3
"""Compara o banco do bolão (servidor) com a cópia do Neon e traz o que só o Neon tem.

Uso, na pasta do projeto (o .env aponta para o banco do site):
    cd ~/bolao-brasileirao
    .venv/bin/python ~/juntar_neon.py              # só compara: relatório, nada é gravado
    .venv/bin/python ~/juntar_neon.py --aplicar    # grava (pede confirmação)

Lê o Neon do banco local "bolao_neon" (restaurado do dump); --neon-db muda o nome.

Regras ao aplicar:
- palpite que só existe no Neon: é criado no banco do site;
- palpite diferente nos dois: vale o lado alterado por último; o jogador do 1º gol
  preenchido num lado e vazio no outro é mantido (ex.: conferência do 1º gol);
- resultado que só existe no Neon: é criado; resultado diferente nos dois: só aparece no
  relatório (não há data de alteração para decidir);
- primeiro marcador preenchido só no Neon: é copiado;
- participações, bônus e jogos novos diferentes: só aparecem no relatório.
Cada palpite gravado fica no histórico com o canal "migracao_neon".
"""
import argparse
import csv
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.getcwd())  # roda a partir da pasta do projeto

CAMPOS_PALPITE = ("gols_casa", "gols_fora", "penaltis_casa", "penaltis_fora", "primeiro_gol", "situacao")
CAMPOS_RESULTADO = ("gols_casa_real", "gols_fora_real", "penaltis_casa_real", "penaltis_fora_real")
CONSULTAS = {
    "rodada": "SELECT id, nome, campeonato_id FROM rodada",
    "jogo": "SELECT id, rodada_id, time_casa, time_fora, classico, primeiro_marcador FROM jogo",
    "participacao": ("SELECT id, bolao_id, nome_exibicao, status, rodada_entrada_id, rodada_desistencia_id "
                     "FROM participacao"),
    "palpite": ("SELECT id, participacao_id, jogo_id, gols_casa, gols_fora, penaltis_casa, penaltis_fora, "
                "primeiro_gol, situacao, atualizado_em FROM palpite"),
    "resultado": ("SELECT jogo_id, gols_casa_real, gols_fora_real, penaltis_casa_real, penaltis_fora_real, "
                  "primeiro_gol_real FROM resultado"),
    "bonus": "SELECT participacao_id, rodada_id, pontos FROM bonus_rodada",
}


def carregar(conexao):
    from sqlalchemy import text
    return {nome: [dict(l) for l in conexao.execute(text(sql)).mappings()] for nome, sql in CONSULTAS.items()}


def vazio(valor):
    return valor is None or str(valor).strip() == ""


class Banco:
    """Linhas de um banco indexadas por chaves naturais (iguais nos dois lados)."""

    def __init__(self, dados):
        self.rodadas = {r["id"]: r for r in dados["rodada"]}
        self.jogos = {j["id"]: j for j in dados["jogo"]}
        self.partes = {p["id"]: p for p in dados["participacao"]}
        self.chave_rodada = {r["id"]: (r["campeonato_id"], r["nome"]) for r in dados["rodada"]}
        self.chave_jogo = {j["id"]: (self.chave_rodada.get(j["rodada_id"]), j["time_casa"], j["time_fora"])
                           for j in dados["jogo"]}
        self.chave_parte = {p["id"]: (p["bolao_id"], p["nome_exibicao"]) for p in dados["participacao"]}
        self.jogo_por_chave = {c: i for i, c in self.chave_jogo.items()}
        self.parte_por_chave = {c: i for i, c in self.chave_parte.items()}
        self.palpites = {(self.chave_parte[p["participacao_id"]], self.chave_jogo[p["jogo_id"]]): p
                         for p in dados["palpite"]}
        self.resultados = {self.chave_jogo[r["jogo_id"]]: r for r in dados["resultado"]}
        self.bonus = {(self.chave_parte[b["participacao_id"]], self.chave_rodada[b["rodada_id"]]): b
                      for b in dados["bonus"]}


def nome_jogo(chave):
    rodada, casa, fora = chave
    return f"{rodada[1] if rodada else '?'} · {casa} x {fora}"


def mesclar_palpite(local, neon):
    """Valores finais de um palpite diferente nos dois lados e o lado que prevaleceu."""
    neon_mais_novo = str(neon["atualizado_em"] or "") > str(local["atualizado_em"] or "")
    base, outro = (neon, local) if neon_mais_novo else (local, neon)
    final = {c: base[c] for c in CAMPOS_PALPITE}
    if vazio(final["primeiro_gol"]) and not vazio(outro["primeiro_gol"]):
        final["primeiro_gol"] = outro["primeiro_gol"]
    return final, "neon" if neon_mais_novo else "local"


def comparar(local, neon):
    """Lista de diferenças: dicts com tipo, onde, descrição dos dois lados e a decisão."""
    difs = []

    def anotar(tipo, onde, valor_local, valor_neon, decisao, **acao):
        difs.append({"tipo": tipo, "onde": onde, "local": valor_local, "neon": valor_neon,
                     "decisao": decisao, **acao})

    for chave, p in neon.partes.items():
        ck = neon.chave_parte[chave]
        if ck not in local.parte_por_chave:
            anotar("participacao", p["nome_exibicao"], "-", "existe", "revisar: só no Neon")
            continue
        lp = local.partes[local.parte_por_chave[ck]]
        for campo in ("status", "rodada_entrada_id", "rodada_desistencia_id"):
            if lp[campo] != p[campo]:
                anotar("participacao", f"{p['nome_exibicao']} ({campo})", lp[campo], p[campo], "revisar")

    for chave_j, j in neon.jogos.items():
        cj = neon.chave_jogo[chave_j]
        if cj not in local.jogo_por_chave:
            anotar("jogo", nome_jogo(cj), "-", "existe", "revisar: jogo só no Neon")
            continue
        lj = local.jogos[local.jogo_por_chave[cj]]
        if bool(lj["classico"]) != bool(j["classico"]):
            anotar("jogo", f"{nome_jogo(cj)} (clássico)", lj["classico"], j["classico"], "revisar")
        if not vazio(j["primeiro_marcador"]) and vazio(lj["primeiro_marcador"]):
            anotar("marcador", nome_jogo(cj), "-", j["primeiro_marcador"], "copiar do Neon",
                   jogo_id=lj["id"], marcador=j["primeiro_marcador"])
        elif not vazio(j["primeiro_marcador"]) and lj["primeiro_marcador"] != j["primeiro_marcador"]:
            anotar("marcador", nome_jogo(cj), lj["primeiro_marcador"], j["primeiro_marcador"], "manter o local")

    for cj, r in neon.resultados.items():
        lr = local.resultados.get(cj)
        texto = lambda x: f"{x['gols_casa_real']}x{x['gols_fora_real']}" + (
            f" ({x['penaltis_casa_real']}x{x['penaltis_fora_real']} pên.)" if x["penaltis_casa_real"] is not None else "")
        if lr is None:
            if cj in local.jogo_por_chave:
                valores = {c: r[c] for c in CAMPOS_RESULTADO}
                if not vazio(r["primeiro_gol_real"]):
                    valores["primeiro_gol_real"] = r["primeiro_gol_real"]
                anotar("resultado", nome_jogo(cj), "-", texto(r), "copiar do Neon",
                       jogo_id=local.jogo_por_chave[cj], valores=valores)
        elif any(lr[c] != r[c] for c in CAMPOS_RESULTADO):
            anotar("resultado", nome_jogo(cj), texto(lr), texto(r), "revisar: placares diferentes")

    for chave, p in neon.palpites.items():
        (bolao, nome), cj = chave
        onde = f"{nome} · {nome_jogo(cj)}"
        texto = lambda x: f"{x['gols_casa']}x{x['gols_fora']}" + (
            f" ★ {x['primeiro_gol']}" if not vazio(x["primeiro_gol"]) else "") + (
            f" [{x['situacao']}]" if x["situacao"] not in (None, "valido") else "")
        lp = local.palpites.get(chave)
        if lp is None:
            if (bolao, nome) in local.parte_por_chave and cj in local.jogo_por_chave:
                anotar("palpite", onde, "-", texto(p), "copiar do Neon",
                       participacao_id=local.parte_por_chave[(bolao, nome)], jogo_id=local.jogo_por_chave[cj],
                       valores={c: p[c] for c in CAMPOS_PALPITE})
            continue
        if all((lp[c] or None) == (p[c] or None) for c in CAMPOS_PALPITE):
            continue
        final, lado = mesclar_palpite(lp, p)
        if all((final[c] or None) == (lp[c] or None) for c in CAMPOS_PALPITE):
            anotar("palpite", onde, texto(lp), texto(p), "manter o local (mais recente)")
        else:
            anotar("palpite", onde, texto(lp), texto(p),
                   "usar o Neon (mais recente)" if lado == "neon" else "manter o local + 1º gol do Neon",
                   palpite_id=lp["id"], valores=final)

    for chave, b in neon.bonus.items():
        lb = local.bonus.get(chave)
        if lb is None or lb["pontos"] != b["pontos"]:
            (bolao, nome), rodada = chave
            anotar("bonus", f"{nome} · {rodada[1]}", lb["pontos"] if lb else "-", b["pontos"], "revisar")

    so_local = [k for k in local.palpites if k not in neon.palpites]
    return difs, so_local


def aplicar(difs):
    """Grava as diferenças marcadas para copiar/usar o Neon. Devolve (gravados, falhas)."""
    from database import db
    from models import Jogo, Palpite, Resultado
    gravados, falhas = Counter(), []
    for d in difs:
        if not any(k in d for k in ("palpite_id", "participacao_id", "marcador")) and \
                not (d["tipo"] == "resultado" and "valores" in d):
            continue
        try:
            with db.session.begin_nested():
                if d["tipo"] == "palpite":
                    if "palpite_id" in d:
                        palpite = db.session.get(Palpite, d["palpite_id"])
                    else:
                        palpite = Palpite(participacao_id=d["participacao_id"], jogo_id=d["jogo_id"])
                        db.session.add(palpite)
                    for campo, valor in d["valores"].items():
                        setattr(palpite, campo, valor)
                    palpite.situacao = palpite.situacao or "valido"
                    palpite._canal = "migracao_neon"
                elif d["tipo"] == "resultado":
                    jogo = db.session.get(Jogo, d["jogo_id"])
                    valores = dict(d["valores"])
                    # Sem marcador vindo do Neon, o resultado fica com o marcador que o jogo já tem.
                    if "primeiro_gol_real" not in valores and not vazio(jogo.primeiro_marcador):
                        valores["primeiro_gol_real"] = jogo.primeiro_marcador
                    db.session.add(Resultado(jogo_id=jogo.id, **valores))
                    jogo.encerrado = True
                elif d["tipo"] == "marcador":
                    db.session.get(Jogo, d["jogo_id"]).primeiro_marcador = d["marcador"]
                db.session.flush()
            gravados[d["tipo"]] += 1
        except Exception as erro:  # um item com problema não impede os demais
            falhas.append((d, str(erro)))
    return gravados, falhas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--neon-db", default="bolao_neon", help="banco com a cópia do Neon (padrão: bolao_neon)")
    parser.add_argument("--neon-url", help="URL completa do banco do Neon (substitui --neon-db)")
    parser.add_argument("--aplicar", action="store_true", help="grava as diferenças (pede confirmação)")
    parser.add_argument("--sim", action="store_true", help="não pergunta antes de aplicar")
    parser.add_argument("--saida", type=Path, default=Path.home() / "comparacao-neon.csv")
    args = parser.parse_args(argv)

    from sqlalchemy import create_engine
    from app import create_app
    from database import db

    app = create_app()
    with app.app_context():
        url_neon = args.neon_url or db.engine.url.set(database=args.neon_db)
        motor_neon = create_engine(url_neon)
        with motor_neon.connect() as conexao:
            neon = Banco(carregar(conexao))
        motor_neon.dispose()
        local = Banco(carregar(db.session.connection()))
        difs, so_local = comparar(local, neon)

        with args.saida.open("w", newline="", encoding="utf-8-sig") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")
            escritor.writerow(["tipo", "onde", "servidor", "neon", "decisao"])
            for d in difs:
                escritor.writerow([d["tipo"], d["onde"], d["local"], d["neon"], d["decisao"]])

        print(f"Palpites: {len(local.palpites)} no servidor, {len(neon.palpites)} no Neon; "
              f"{len(so_local)} só no servidor (ficam como estão).")
        for (tipo, decisao), total in sorted(Counter((d["tipo"], d["decisao"]) for d in difs).items()):
            print(f"  {tipo}: {decisao}: {total}")
        if not difs:
            print("Nenhuma diferença vinda do Neon.")
        for d in difs:
            if d["decisao"].startswith("revisar"):
                print(f"    [revisar] {d['tipo']} · {d['onde']}: servidor {d['local']} | Neon {d['neon']}")
        print(f"Relatório completo: {args.saida}")

        if not args.aplicar:
            print("Comparação apenas: nada foi gravado. Rode de novo com --aplicar para gravar.")
            return 0
        if not args.sim and input("Gravar no banco do site? Digite 'sim': ").strip().lower() != "sim":
            print("Cancelado: nada foi gravado.")
            return 1
        gravados, falhas = aplicar(difs)
        db.session.commit()
        print("Gravado: " + (", ".join(f"{t}: {n}" for t, n in gravados.items()) or "nada"))
        for d, erro in falhas:
            print(f"  Não gravado ({d['tipo']} · {d['onde']}): {erro}")
        print("Reinicie o site para atualizar a classificação: sudo systemctl restart bolao")
    return 0


if __name__ == "__main__":
    sys.exit(main())
