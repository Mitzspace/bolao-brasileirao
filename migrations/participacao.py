"""002: entrada por rodada, desistência e histórico, com backup e reversão segura.

SQLite apenas. Não inicializa Flask. DDL e dados são alterados na mesma transação
EXCLUSIVE, sem substituir o arquivo que outra conexão possa ter aberto.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import sqlite3
from types import SimpleNamespace

from services.pontuacao import calcular_pontuacao

VERSAO = "002_participacao_desistencia"
CAMPOS_PARTICIPACAO = {
    "rodada_entrada_id": "INTEGER REFERENCES rodada(id)",
    "rodada_desistencia_id": "INTEGER REFERENCES rodada(id)",
    "motivo_desistencia": "TEXT",
    "desistencia_registrada_em": "DATETIME",
    "desistencia_registrada_por": "INTEGER REFERENCES participante(id)",
    "observacao": "TEXT",
}
STATUS_ANTIGO = "status IN ('ativo', 'saiu', 'removido')"
STATUS_NOVO = "status IN ('ativo', 'saiu', 'removido', 'desistente')"


def identificar(valor):
    return '"' + valor.replace('"', '""') + '"'


def abrir(path, leitura=False):
    con = sqlite3.connect(Path(path).resolve().as_uri() + ("?mode=ro" if leitura else "?mode=rw"),
                          uri=True, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def snapshot(con):
    schema = [dict(r) for r in con.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]
    dados = {s["name"]: [dict(r) for r in con.execute(
        f'SELECT * FROM {identificar(s["name"])} ORDER BY id')]
        for s in schema if s["type"] == "table"}
    return {"schema": schema, "dados": dados}


def digest(estado):
    return hashlib.sha256(json.dumps(estado, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def verificar_integridade(con):
    if con.execute("PRAGMA quick_check").fetchone()[0] != "ok" or con.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("Banco com erro de integridade ou referências inválidas.")


def ler(path):
    with closing(abrir(path, True)) as con:
        con.execute("BEGIN")
        verificar_integridade(con)
        return snapshot(con)


def ranking(dados):
    """Compara cada participação, geral E por rodada, incluindo créditos legados."""
    jogos = {j["id"]: j for j in dados["jogo"]}
    resultados = {r["jogo_id"]: r for r in dados["resultado"]}
    totais = {(p["id"], 0): [0, 0, 0] for p in dados["participacao"]}
    for palpite in dados["palpite"]:
        jogo = jogos[palpite["jogo_id"]]
        if jogo["id"] not in resultados:
            continue
        detalhe = calcular_pontuacao(SimpleNamespace(**palpite), SimpleNamespace(**jogo),
                                     SimpleNamespace(**resultados[jogo["id"]]))
        for rodada_id in (0, jogo["rodada_id"]):
            total = totais.setdefault((palpite["participacao_id"], rodada_id), [0, 0, 0])
            total[0] += detalhe.total
            total[1] += int(detalhe.placar_exato)
            total[2] += int(detalhe.acertou_resultado and not detalhe.placar_exato)
    for bonus in dados["bonus_rodada"]:
        for rodada_id in (0, bonus["rodada_id"]):
            totais.setdefault((bonus["participacao_id"], rodada_id), [0, 0, 0])[0] += bonus["pontos"]
    return totais


def aplicado(estado):
    return any(r["id"] == VERSAO for r in estado["dados"].get("_schema_migrations", []))


def plano(estado):
    dados = estado["dados"]
    if aplicado(estado):
        return {"status": "já migrado", "versao": VERSAO}
    obrigatorias = {"bolao", "participacao", "participante", "palpite", "palpite_log",
                    "bonus_rodada", "jogo", "resultado", "rodada", "campeonato", "_schema_migrations"}
    permitidas = obrigatorias | {"classificacao_cache"}
    if not obrigatorias.issubset(dados) or set(dados) - permitidas:
        raise ValueError("Schema incompatível: exige a fundação multi-bolão sem migração parcial.")
    sql = next(s["sql"] for s in estado["schema"] if s["name"] == "participacao")
    if STATUS_ANTIGO not in sql or any(c in sql for c in CAMPOS_PARTICIPACAO):
        raise ValueError("Schema de participação inesperado ou parcialmente migrado.")
    if any(s["type"] in {"trigger", "view"} for s in estado["schema"]):
        raise ValueError("Views/triggers adicionais exigem revisão antes de migrar.")
    totais = ranking(dados)
    return {"status": "pronto", "versao": VERSAO,
            "contagens": {t: len(rows) for t, rows in dados.items()},
            "pontos_totais": sum(v[0] for (p, r), v in totais.items() if r == 0),
            "politica_entrada_tardia": "fora_da_conta", "origem_sha256": digest(estado)}


def backup(origem, destino):
    destino = Path(destino).resolve()
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Reserva exclusiva: jamais sobrescrever um backup.
    with destino.open("xb"):
        pass
    with closing(abrir(origem, True)) as src, closing(sqlite3.connect(destino)) as dst:
        src.backup(dst)
    return destino


def verificar_preservacao(antes, depois):
    for tabela, rows in antes["dados"].items():
        novas = {r["id"]: r for r in depois["dados"][tabela]}
        if tabela != "_schema_migrations" and len(rows) != len(novas):
            raise ValueError(f"Contagem alterada: {tabela}")
        for row in rows:
            if any(novas[row["id"]][k] != v for k, v in row.items()):
                raise ValueError(f"Dado anterior alterado: {tabela}/{row['id']}")
    if ranking(antes["dados"]) != ranking(depois["dados"]):
        raise ValueError("Ranking geral ou por rodada alterado.")


def alterar_schema(con, antes):
    # FKs desligadas antes do BEGIN; verificadas novamente antes do COMMIT.
    sql = next(s["sql"] for s in antes["schema"] if s["name"] == "participacao")
    novo_sql = re.sub(r'^CREATE TABLE\s+"?participacao"?', 'CREATE TABLE participacao_etapa1', sql, count=1)
    if novo_sql == sql:
        raise ValueError("DDL de participação desconhecido.")
    novo_sql = novo_sql.replace(STATUS_ANTIGO, STATUS_NOVO)
    # Colunas devem preceder as constraints de tabela do DDL SQLAlchemy.
    pos = novo_sql.index("(") + 1
    novo_sql = novo_sql[:pos] + "\n" + ",\n".join(
        f"{nome} {tipo}" for nome, tipo in CAMPOS_PARTICIPACAO.items()) + ",\n" + novo_sql[pos:]
    con.execute(novo_sql)
    cols = ",".join(identificar(r[1]) for r in con.execute("PRAGMA table_info(participacao)"))
    con.execute(f"INSERT INTO participacao_etapa1 ({cols}) SELECT {cols} FROM participacao")
    con.execute("DROP TABLE participacao")
    con.execute("ALTER TABLE participacao_etapa1 RENAME TO participacao")
    for s in antes["schema"]:
        if s["type"] == "index" and s["tbl_name"] == "participacao" and s["sql"]:
            con.execute(s["sql"])
    con.execute("ALTER TABLE bolao ADD COLUMN politica_entrada_tardia VARCHAR(20) NOT NULL "
                "DEFAULT 'fora_da_conta' CONSTRAINT bolao_entrada_tardia "
                "CHECK (politica_entrada_tardia IN ('zero', 'fora_da_conta'))")
    con.execute("ALTER TABLE palpite ADD COLUMN excluido_por_desistencia BOOLEAN NOT NULL DEFAULT 0")
    con.execute("""CREATE TABLE participacao_log (
        id INTEGER PRIMARY KEY NOT NULL,
        participacao_id INTEGER NOT NULL REFERENCES participacao(id),
        alterado_por INTEGER REFERENCES participante(id),
        alterado_em DATETIME NOT NULL,
        acao VARCHAR(32) NOT NULL,
        valores_anteriores TEXT,
        valores_novos TEXT NOT NULL
    )""")
    con.execute("INSERT INTO _schema_migrations (id, aplicado_em) VALUES (?,?)",
                (VERSAO, datetime.now(timezone.utc).isoformat()))


def upgrade(path):
    path = Path(path).resolve()
    antes = ler(path)
    resumo = plano(antes)
    if aplicado(antes):
        return resumo
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + secrets.token_hex(4)
    copia = backup(path, path.parent / "backups" / f"{path.stem}.antes-participacao-{tag}.db")
    if digest(ler(copia)) != digest(antes):
        raise ValueError("Banco mudou durante o backup; execute novamente em manutenção.")
    manifesto = copia.with_suffix(".json")
    with closing(abrir(path)) as con:
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("BEGIN EXCLUSIVE")
        try:
            if digest(snapshot(con)) != digest(antes):
                raise ValueError("Banco mudou antes da migração; nenhuma alteração aplicada.")
            alterar_schema(con, antes)
            verificar_integridade(con)
            depois = snapshot(con)
            verificar_preservacao(antes, depois)
            info = {"versao": VERSAO, "banco": str(path), "backup": str(copia),
                    "sha_antes": digest(antes), "sha_depois": digest(depois), "resumo": resumo}
            # Manifesto pronto antes do commit. Se o commit falhar, hashes impedem rollback indevido.
            with manifesto.open("x", encoding="utf-8") as arquivo:
                json.dump(info, arquivo, ensure_ascii=False, indent=2)
            con.commit()
        except Exception:
            con.rollback()
            raise
    return {**resumo, "status": "migrado", "backup": str(copia), "manifesto": str(manifesto)}


def rollback(path, manifesto):
    path = Path(path).resolve()
    info = json.loads(Path(manifesto).read_text(encoding="utf-8"))
    if info["versao"] != VERSAO or Path(info["banco"]).resolve() != path:
        raise ValueError("Manifesto de outro banco ou versão.")
    original = ler(info["backup"])
    if digest(original) != info["sha_antes"]:
        raise ValueError("Backup alterado ou incompatível.")
    with closing(abrir(path)) as con:
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("BEGIN EXCLUSIVE")
        try:
            atual = snapshot(con)
            if digest(atual) != info["sha_depois"]:
                raise ValueError("Há dados novos/alterados após a migração; reversão recusada para preservar histórico.")
            for nome in atual["dados"]:
                con.execute(f"DROP TABLE {identificar(nome)}")
            for s in original["schema"]:
                if s["type"] == "table":
                    con.execute(s["sql"])
            for tabela, rows in original["dados"].items():
                if not rows:
                    continue
                cols = list(rows[0])
                con.executemany(f'INSERT INTO {identificar(tabela)} (' +
                    ",".join(identificar(c) for c in cols) + ") VALUES (" + ",".join("?" for _ in cols) + ")",
                    [[r[c] for c in cols] for r in rows])
            for s in original["schema"]:
                if s["type"] != "table" and s["sql"]:
                    con.execute(s["sql"])
            verificar_integridade(con)
            if digest(snapshot(con)) != info["sha_antes"]:
                raise ValueError("Reversão não reproduz o schema e dados originais.")
            con.commit()
        except Exception:
            con.rollback()
            raise
    return {"status": "revertido", "sha256": digest(original)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["plan", "preview", "upgrade", "rollback"])
    parser.add_argument("--database", type=Path, default=Path("instance/banco.db"))
    parser.add_argument("--directory", type=Path, default=Path("instance/validacao_participacao"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--app-parado", action="store_true")
    args = parser.parse_args()
    if args.acao == "plan":
        resultado = plano(ler(args.database))
    elif args.acao == "preview":
        copia = backup(args.database, args.directory / f"ensaio-{secrets.token_hex(4)}.db")
        resultado = {"copia": str(copia), **upgrade(copia)}
        if "manifesto" in resultado:
            resultado["reversao"] = rollback(copia, resultado["manifesto"])
            resultado["reaplicacao"] = upgrade(copia)
    elif not args.app_parado:
        parser.error("Pare o Flask e gravadores antes de usar upgrade/rollback; informe --app-parado.")
    elif args.acao == "upgrade":
        resultado = upgrade(args.database)
    elif not args.manifest:
        parser.error("rollback exige --manifest")
    else:
        resultado = rollback(args.database, args.manifest)
    print(json.dumps(resultado, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
