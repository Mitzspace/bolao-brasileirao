"""Migração SQLite explícita: planejar, ensaiar, aplicar com backup e reverter.

Não inicializa o Flask e nunca executa create_app no banco de origem.
"""
import argparse
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from contextlib import closing

from services.pontuacao import calcular_pontuacao

VERSAO = "001_multi_bolao"
TABELAS_LEGADAS = {"participante", "campeonato", "rodada", "jogo", "palpite",
                   "resultado", "bonus_rodada", "classificacao_cache"}


def abrir_leitura(path):
    con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def snapshot(con):
    tabelas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {t: [dict(r) for r in con.execute(f'SELECT * FROM "{t}" ORDER BY id')]
            for t in tabelas if t != "_schema_migrations"}


def digest(dados):
    return hashlib.sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ler(path):
    with closing(abrir_leitura(path)) as con:
        if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Banco com erro de integridade.")
        if con.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Banco com referências inválidas.")
        return snapshot(con)


def ranking(dados, novo=False):
    jogos = {j["id"]: j for j in dados["jogo"]}
    resultados = {r["jogo_id"]: r for r in dados["resultado"]}
    totais = {p["id"]: {"pontos": 0, "cravadas": 0, "acertos": 0, "bonus": 0} for p in dados["participante"]}
    for p in dados["palpite"]:
        if p["jogo_id"] not in resultados:
            continue
        r, j = resultados[p["jogo_id"]], jogos[p["jogo_id"]]
        pal = SimpleNamespace(**p)
        jogo = SimpleNamespace(classico=bool(j["classico"] if novo else j["especial"]),
                               primeiro_marcador=j.get("primeiro_marcador") if novo else r["primeiro_gol_real"])
        # Reproduz a regra anterior para comparar o histórico, sem reinterpretá-lo.
        if not novo and not jogo.classico:
            jogo.primeiro_marcador = None
        detalhe = calcular_pontuacao(pal, jogo, SimpleNamespace(**r))
        total = totais[p["participante_id"]]
        total["pontos"] += detalhe.total
        total["cravadas"] += int(detalhe.placar_exato)
        total["acertos"] += int(detalhe.acertou_resultado and not detalhe.placar_exato)
    for b in dados["bonus_rodada"]:
        totais[b["participante_id"]]["bonus"] += b["pontos"]
        totais[b["participante_id"]]["pontos"] += b["pontos"]
    return totais


def plano(dados, global_id=1, responsaveis=(22,), sem_conta=(3,)):
    if set(dados) - TABELAS_LEGADAS:
        raise ValueError("Há tabelas desconhecidas ou o banco já foi migrado; nenhuma mudança executada.")
    obrigatorias = TABELAS_LEGADAS - {"classificacao_cache"}
    if not obrigatorias.issubset(dados):
        raise ValueError("Schema legado incompatível.")
    if len(dados["campeonato"]) != 1:
        raise ValueError("Esta migração inicial exige exatamente um campeonato.")
    pessoas = {p["id"]: p for p in dados["participante"]}
    if not {global_id, *responsaveis, *sem_conta}.issubset(pessoas):
        raise ValueError("Um responsável informado não existe.")
    if global_id in sem_conta or set(responsaveis) & set(sem_conta):
        raise ValueError("Papéis de conta conflitantes.")
    ids_login = {global_id, *responsaveis}
    if any(p["admin"] and p["id"] not in ids_login for p in pessoas.values()):
        raise ValueError("Há administrador não incluído no mapeamento explícito.")
    return {
        "versao": VERSAO, "contagens": {t: len(v) for t, v in dados.items()},
        "admin_global_id": global_id, "contas_vinculadas": sorted(ids_login),
        "responsaveis_sem_conta": list(sem_conta),
        "participacoes": len(pessoas),
        "pontos_totais": sum(p["pontos"] for p in ranking(dados).values()),
        "bonus_preservado": sum(b["pontos"] for b in dados["bonus_rodada"]),
        "origem_sha256": digest(dados),
    }


def transformar(dados, global_id=1, responsaveis=(22,), sem_conta=(3,)):
    plano(dados, global_id, responsaveis, sem_conta)
    novo = json.loads(json.dumps(dados))
    agora = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(" ")
    campeonato = dados["campeonato"][0]
    ids_login = {global_id, *responsaveis}
    ids_responsavel = ids_login | set(sem_conta)
    for p in novo["participante"]:
        p.update(admin_global=p["id"] == global_id, conta_ativa=p["id"] in ids_login)
    novo["bolao"] = [{"id": 1, "nome": campeonato["nome"], "campeonato_id": campeonato["id"],
                      "criador_id": global_id, "codigo_convite": secrets.token_urlsafe(32),
                      "permite_palpite_proprio": False, "permite_lancamento_por_responsavel": True,
                      "status": "ativo", "criado_em": agora, "pontua_desde_entrada": True}]
    # Data de entrada real é desconhecida; histórico anterior continua válido.
    novo["participacao"] = [{"id": p["id"], "bolao_id": 1,
        "usuario_id": p["id"] if p["id"] in ids_login else None,
        "participante_legado_id": p["id"], "nome_exibicao": p["nome"],
        "papel": "responsavel" if p["id"] in ids_responsavel else "participante",
        "status": "ativo", "entrou_em": None, "entrada_legada": True,
        "pontua_desde": None, "saiu_em": None, "codigo_vinculo": None}
        for p in dados["participante"]]
    resultados = {r["jogo_id"]: r for r in dados["resultado"]}
    for j in novo["jogo"]:
        j.update(classico=bool(j["especial"]), primeiro_marcador=resultados.get(j["id"], {}).get("primeiro_gol_real"))
    novo["palpite_log"] = []
    for p in novo["palpite"]:
        p.update(participacao_id=p["participante_id"], origem=None, lancado_por=None,
                 criado_em=None, atualizado_em=None, recebido_em=None,
                 lancado_apos_inicio=False, auditoria_legada=True)
        novos = {k: p[k] for k in ("participacao_id", "gols_casa", "gols_fora", "origem", "lancado_por", "recebido_em", "lancado_apos_inicio", "auditoria_legada")}
        novos["jogador_primeiro_gol"] = p["primeiro_gol"]
        novo["palpite_log"].append({"id": len(novo["palpite_log"]) + 1, "palpite_id": p["id"],
            "alterado_por": None, "alterado_em": agora, "acao": "migracao",
            "valores_anteriores": None, "valores_novos": json.dumps(novos, ensure_ascii=False, sort_keys=True)})
    for b in novo["bonus_rodada"]:
        b.update(participacao_id=b["participante_id"], historico=True)
    if ranking(dados) != ranking(novo, novo=True):
        raise ValueError("O ranking mudaria com as regras confirmadas. Reconcilie antes de migrar.")
    return novo


def verificar_preservacao(antes, depois):
    for tabela, linhas in antes.items():
        novas = {r["id"]: r for r in depois[tabela]}
        if len(linhas) != len(novas):
            raise ValueError(f"Contagem alterada: {tabela}")
        for row in linhas:
            if any(novas[row["id"]][k] != v for k, v in row.items()):
                raise ValueError(f"Dado legado alterado: {tabela}/{row['id']}")
    if ranking(antes) != ranking(depois, novo=True):
        raise ValueError("Ranking individual alterado.")


def backup_sqlite(origem, destino):
    destino = Path(destino).resolve()
    if destino.exists():
        raise ValueError("Backup já existe; não será sobrescrito.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with closing(abrir_leitura(origem)) as src, closing(sqlite3.connect(destino)) as dst:
        src.backup(dst)
        dst.commit()
    return destino


def construir(path, dados):
    with closing(sqlite3.connect(path)) as con:
        con.execute("PRAGMA foreign_keys=ON")
        # A migração 001 não deve incorporar silenciosamente campos de versões futuras.
        con.executescript(Path(__file__).with_name("sql").joinpath(
            "001_multi_bolao.sql").read_text(encoding="utf-8"))
        con.execute("BEGIN")
        con.execute("PRAGMA defer_foreign_keys=ON")
        for nome, rows in dados.items():
            if rows:
                cols = list(rows[0])
                sql = f'INSERT INTO "{nome}" (' + ",".join(f'"{c}"' for c in cols) + ") VALUES (" + ",".join("?" for _ in cols) + ")"
                con.executemany(sql, [[r[c] for c in cols] for r in rows])
        con.execute("INSERT INTO _schema_migrations VALUES (?,?)", (VERSAO, datetime.now(timezone.utc).isoformat()))
        con.commit()
    return ler(path)


def upgrade(path, global_id=1, responsaveis=(22,), sem_conta=(3,)):
    path = Path(path).resolve()
    with closing(abrir_leitura(path)) as con:
        if "_schema_migrations" in [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
            versoes = [r[0] for r in con.execute("SELECT id FROM _schema_migrations")]
            if VERSAO in versoes:
                return {"status": "já migrado", "versao": VERSAO}
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ValueError("Banco em uso/WAL pendente. Pare o app e finalize as conexões antes de migrar.")
    dados = ler(path)
    resumo = plano(dados, global_id, responsaveis, sem_conta)
    novo = transformar(dados, global_id, responsaveis, sem_conta)
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + secrets.token_hex(4)
    backup = backup_sqlite(path, path.parent / "backups" / f"{path.stem}.antes-fase1-{tag}.db")
    if digest(ler(backup)) != digest(dados):
        raise ValueError("Banco mudou durante o backup; migração cancelada.")
    temporario = path.parent / f"{path.stem}.fase1-preparado-{tag}.db"
    preparado = construir(temporario, novo)
    verificar_preservacao(dados, preparado)
    if digest(ler(path)) != digest(dados):
        raise ValueError("Banco mudou durante a preparação; migração cancelada.")
    manifesto = backup.with_suffix(".json")
    info = {"versao": VERSAO, "banco": str(path), "backup": str(backup),
            "sha_antes": digest(dados), "sha_depois": digest(preparado), "resumo": resumo}
    manifesto.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, path)
    return {"status": "migrado", "backup": str(backup), "manifesto": str(manifesto), **resumo}


def rollback(path, manifesto):
    path = Path(path).resolve()
    info = json.loads(Path(manifesto).read_text(encoding="utf-8"))
    if info["versao"] != VERSAO or Path(info["banco"]).resolve() != path:
        raise ValueError("Manifesto de outro banco ou versão.")
    if digest(ler(path)) != info["sha_depois"]:
        raise ValueError("Há dados novos/alterados após a migração. Reversão recusada para não perder histórico.")
    if digest(ler(info["backup"])) != info["sha_antes"]:
        raise ValueError("Backup alterado ou incompatível.")
    for suffix in ("-wal", "-journal"):
        sidecar = Path(str(path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ValueError("Banco em uso. Pare o app antes de reverter.")
    destino = path.parent / f"{path.stem}.restaurado-{secrets.token_hex(4)}.db"
    backup_sqlite(info["backup"], destino)
    os.replace(destino, path)
    return {"status": "revertido", "sha256": digest(ler(path))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["plan", "preview", "upgrade", "rollback"])
    parser.add_argument("--database", type=Path, default=Path("instance/banco.db"))
    parser.add_argument("--directory", type=Path, default=Path("instance/validacao_fase1"))
    parser.add_argument("--admin-global-id", type=int, default=1)
    parser.add_argument("--responsavel-id", type=int, action="append")
    parser.add_argument("--responsavel-sem-conta-id", type=int, action="append")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--app-parado", action="store_true", help="Confirma manutenção sem conexões ao banco")
    args = parser.parse_args()
    kw = dict(global_id=args.admin_global_id, responsaveis=args.responsavel_id or (22,),
              sem_conta=args.responsavel_sem_conta_id or (3,))
    if args.acao == "plan":
        result = plano(ler(args.database), **kw)
    elif args.acao == "preview":
        args.directory.mkdir(parents=True, exist_ok=True)
        copia = args.directory / f"ensaio-{secrets.token_hex(4)}.db"
        backup_sqlite(args.database, copia)
        result = {"copia": str(copia.resolve()), **upgrade(copia, **kw)}
    elif not args.app_parado:
        parser.error("upgrade/rollback exigem --app-parado; pare o Flask antes de executar")
    elif args.acao == "upgrade":
        result = upgrade(args.database, **kw)
    else:
        if not args.manifest:
            parser.error("rollback exige --manifest")
        result = rollback(args.database, args.manifest)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
