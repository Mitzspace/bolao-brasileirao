"""Exporta do Neon (somente leitura) os dados usados no cálculo da pontuação.

Uso, na pasta do projeto:
    python conferir_neon.py

Gera instance/neon_export.json. Não grava nada no banco: a sessão é aberta
como somente leitura e só faz SELECT. Senhas e e-mails não são exportados.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENV = RAIZ / ".env.neon.local"
SAIDA = RAIZ / "instance" / "neon_export.json"

CONSULTAS = {
    "bolao": """select id, nome, campeonato_id, status, politica_entrada_tardia,
                pontos_comum_exato, pontos_comum_resultado, pontos_classico_exato,
                pontos_classico_resultado, pontos_primeiro_gol from bolao""",
    "participacao": """select id, bolao_id, nome_exibicao, status, rodada_entrada_id,
                       rodada_desistencia_id from participacao""",
    "rodada": "select id, nome, campeonato_id from rodada",
    "jogo": """select id, rodada_id, time_casa, time_fora, classico, especial,
               primeiro_marcador, encerrado, data from jogo""",
    "resultado": "select id, jogo_id, gols_casa_real, gols_fora_real from resultado",
    "palpite": """select id, participacao_id, jogo_id, gols_casa, gols_fora, primeiro_gol,
                  situacao, excluido_por_desistencia, criado_em, atualizado_em from palpite""",
    "bonus_rodada": "select id, participacao_id, rodada_id, pontos, motivo, historico from bonus_rodada",
}


def ler_url():
    if not ENV.exists():
        sys.exit(f"Arquivo não encontrado: {ENV}")
    valores = {}
    for linha in ENV.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            valores[chave.strip()] = valor.strip().strip('"').strip("'")
    url = valores.get("MIGRATION_DATABASE_URL") or valores.get("DATABASE_URL")
    if not url or url.startswith("${"):
        sys.exit("Não achei MIGRATION_DATABASE_URL em .env.neon.local")
    return url


def conectar(url):
    try:
        import psycopg
        conexao = psycopg.connect(url, connect_timeout=15)
        conexao.read_only = True
        return conexao
    except ImportError:
        pass
    try:
        import psycopg2
        conexao = psycopg2.connect(url, connect_timeout=15)
        conexao.set_session(readonly=True)
        return conexao
    except ImportError:
        sys.exit('Instale o driver do PostgreSQL:  pip install "psycopg[binary]"')


def main():
    conexao = conectar(ler_url())
    dados = {}
    try:
        cursor = conexao.cursor()
        for tabela, sql in CONSULTAS.items():
            cursor.execute(sql)
            colunas = [c[0] for c in cursor.description]
            dados[tabela] = [dict(zip(colunas, linha)) for linha in cursor.fetchall()]
            print(f"{tabela}: {len(dados[tabela])} linhas")
    finally:
        conexao.rollback()
        conexao.close()
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, default=str, indent=1), encoding="utf-8")
    print(f"\nPronto: {SAIDA}")


if __name__ == "__main__":
    main()
