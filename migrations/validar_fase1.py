"""Ensaia upgrade/rollback e as telas existentes usando somente cópias do banco."""
import json
import secrets
from pathlib import Path
from flask import template_rendered

from app import create_app
from database import db
from models import Participante, Participacao, Palpite, PalpiteLog
from migrations.fase1 import backup_sqlite, ler, digest, ranking, upgrade, rollback


def validar(origem=Path("instance/banco.db"), diretorio=Path("instance/validacao_fase1")):
    original = ler(origem)
    diretorio.mkdir(parents=True, exist_ok=True)
    copia = diretorio / f"validacao-{secrets.token_hex(4)}.db"
    backup_sqlite(origem, copia)
    resumo = upgrade(copia)
    rollback(copia, resumo["manifesto"])
    assert digest(ler(copia)) == digest(original), "Reversão alterou os dados originais"
    resumo = upgrade(copia)
    assert upgrade(copia)["status"] == "já migrado"
    app = create_app("testing", database_uri="sqlite:///" + copia.resolve().as_posix())
    cliente = app.test_client()
    paginas = {}
    for url in ("/", "/jogos", "/ranking", "/rodada/1/palpites", "/login"):
        paginas[url] = cliente.get(url).status_code
        assert paginas[url] == 200, url
    with cliente.session_transaction() as sess:
        sess["_user_id"] = "1"
        sess["_fresh"] = True
    for url in ("/admin/", "/admin/participantes", "/admin/palpites?participante_id=3&rodada_id=1", "/admin/resultados"):
        paginas[url] = cliente.get(url).status_code
        assert paginas[url] == 200, url
    capturado = []
    def capturar(sender, template, context, **kwargs):
        if "ranking" in context:
            capturado.extend(context["ranking"])
    with template_rendered.connected_to(capturar, app):
        cliente.get("/ranking")
    esperado = ranking(original)
    for item in capturado:
        total = esperado[item["participante"].id]
        assert (item["pontos"], item["cravadas"], item["acertos_vencedor"], item["bonus"]) == (
            total["pontos"], total["cravadas"], total["acertos"], total["bonus"])
    assert len(capturado) == len(esperado)
    with app.app_context():
        assert Participacao.query.count() == 24
        assert Palpite.query.count() == PalpiteLog.query.count() == 5652
        assert Participante.query.filter_by(conta_ativa=True).count() == 2
        albert = Participacao.query.filter_by(participante_legado_id=3).one()
        assert albert.nome_exibicao == "Albert" and albert.usuario_id is None and albert.papel == "responsavel"
        assert db.session.get(Participante, 1).admin_global
        db.session.remove()
        db.engine.dispose()
    assert digest(ler(origem)) == digest(original), "O banco de origem mudou"
    relatorio = {"status": "validado", "copia": str(copia.resolve()),
                 "original_intacto_sha256": digest(original), "reversao": "idêntica ao original",
                 "ranking_individual": "idêntico", "paginas": paginas, "resumo": resumo}
    arquivo = diretorio / "relatorio.json"
    arquivo.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")
    return relatorio


if __name__ == "__main__":
    print(json.dumps(validar(), ensure_ascii=True, indent=2))
