"""Cria uma conta de teste e um bolão de exemplo no banco LOCAL (SQLite), para ver a interface.

    python -m scripts.dados_exemplo

Entrar em http://127.0.0.1:5000/interface/ com:
    e-mail: teste@exemplo.com
    senha:  teste123

Só funciona com banco SQLite (o de desenvolvimento): recusa qualquer outro, para nunca
gravar exemplos no banco de produção. Rodar de novo não duplica nada.
"""
import os
import random
import sys
from datetime import timedelta

os.environ.setdefault("APP_ENV", "development")

from app import create_app  # noqa: E402
from database import db  # noqa: E402
from models import Bolao, Campeonato, Jogo, Palpite, Participacao, Participante, Resultado, Rodada  # noqa: E402
from services.relogio import agora_brasilia  # noqa: E402
from utils import hash_senha  # noqa: E402

EMAIL = "teste@exemplo.com"
SENHA = "teste123"
NOME_BOLAO = "Bolão de Exemplo"

PARTICIPANTES = ["Ana Souza", "Bruno Lima", "Carla Dias", "Diego Rocha", "Elisa Prado",
                 "Fábio Melo", "Gabi Nunes", "Heitor Reis"]

# (casa, fora, clássico) por rodada. As duas primeiras já terminaram; a terceira é a próxima.
RODADAS = [
    [("Flamengo", "Fluminense", True), ("Palmeiras", "Santos", False), ("Grêmio", "Internacional", True),
     ("Bahia", "Vitória", False), ("Cruzeiro", "Botafogo", False)],
    [("Corinthians", "São Paulo", True), ("Fluminense", "Bahia", False), ("Santos", "Grêmio", False),
     ("Internacional", "Cruzeiro", False), ("Vasco", "Flamengo", True)],
    [("Palmeiras", "Corinthians", True), ("Botafogo", "Vasco", False), ("São Paulo", "Santos", False),
     ("Vitória", "Fortaleza", False), ("Atlético-MG", "Cruzeiro", True)],
]
PLACARES = [[(2, 1), (1, 1), (0, 2), (3, 0), (1, 2)], [(1, 0), (2, 2), (0, 1), (3, 1), (1, 1)]]


def criar():
    app = create_app("development", initialize_database=True)
    with app.app_context():
        if db.engine.url.get_backend_name() != "sqlite":
            sys.exit("Recusado: os dados de exemplo só podem ir para o banco local (SQLite).")
        if Participante.query.filter_by(email=EMAIL).first():
            print(f"Os dados de exemplo já existem. Entre com {EMAIL} / {SENHA}.")
            return

        sorteio = random.Random(2026)
        conta = Participante(nome="Responsável Teste", email=EMAIL, senha=hash_senha(SENHA))
        campeonato = Campeonato(nome="Brasileirão (exemplo)", ano=2026, codigo_api=None)
        bolao = Bolao(nome=NOME_BOLAO, campeonato=campeonato, criador=conta)
        db.session.add_all([conta, campeonato, bolao])
        db.session.add(Participacao(bolao=bolao, usuario=conta, nome_exibicao=conta.nome,
                                    papel="responsavel", status="ativo"))
        pessoas = [Participacao(bolao=bolao, nome_exibicao=nome) for nome in PARTICIPANTES]
        db.session.add_all(pessoas)
        db.session.flush()

        agora = agora_brasilia().replace(minute=0, second=0, microsecond=0)
        inicio_rodada = [agora - timedelta(days=14), agora - timedelta(days=7), agora + timedelta(days=3)]
        for numero, jogos in enumerate(RODADAS, start=1):
            rodada = Rodada(nome=f"Rodada {numero}", campeonato=campeonato, aberta=numero == 3)
            db.session.add(rodada)
            encerrada = numero <= len(PLACARES)
            for ordem, (casa, fora, classico) in enumerate(jogos, start=1):
                jogo = Jogo(time_casa=casa, time_fora=fora, classico=classico, rodada=rodada, ordem=ordem,
                            data=inicio_rodada[numero - 1] + timedelta(hours=3 * (ordem - 1)),
                            encerrado=encerrada)
                db.session.add(jogo)
                if encerrada:
                    gc, gf = PLACARES[numero - 1][ordem - 1]
                    db.session.add(Resultado(jogo=jogo, gols_casa_real=gc, gols_fora_real=gf))
                db.session.flush()  # a auditoria dos palpites confere o campeonato do jogo pelo id
                for i, pessoa in enumerate(pessoas):
                    # Na próxima rodada só metade já mandou: aparece a lista de palpites faltantes.
                    if not encerrada and i % 2:
                        continue
                    if encerrada and sorteio.random() < 0.3:
                        gc_p, gf_p = gc, gf  # acerta em cheio de vez em quando
                    else:
                        gc_p, gf_p = sorteio.randint(0, 3), sorteio.randint(0, 2)
                    db.session.add(Palpite(participacao=pessoa, jogo=jogo, gols_casa=gc_p, gols_fora=gf_p,
                                           origem="responsavel", lancado_por=conta.id))
        db.session.commit()
        print(f"Pronto! Bolão '{NOME_BOLAO}' criado com {len(PARTICIPANTES)} participantes e 3 rodadas.")
        print(f"Entre em http://127.0.0.1:5000/interface/ com {EMAIL} / {SENHA}.")


if __name__ == "__main__":
    criar()
