"""
reset_e_importar_oficial.py — Limpa o banco mantendo apenas o usuário William (Admin)
e importa a planilha oficial do bolão (38 rodadas, jogos com placares reais e palpites).
"""

import os
import sys
import re
import openpyxl

sys.path.insert(0, r"c:\Users\Arquivos\Downloads\William\bolao_v2\bolao2")

from app import create_app
from database import db
from models import Campeonato, Jogo, Palpite, Participante, Resultado, Rodada
from werkzeug.security import generate_password_hash


def reset_e_importar():
    app = create_app()
    with app.app_context():
        print("1. Localizando usuário administrador...")
        william = Participante.query.filter_by(email="williambrejauba@gmail.com").first()
        if not william:
            william = Participante.query.filter_by(admin=True).first()
        
        if not william:
            print("ERRO: Usuário admin não encontrado!")
            return

        print(f"Admin preservado: {william.nome} ({william.email}, ID: {william.id})")

        print("2. Limpando dados antigos do banco...")
        Palpite.query.delete()
        Resultado.query.delete()
        Jogo.query.delete()
        Rodada.query.delete()
        Campeonato.query.delete()

        # Remove todos os participantes exceto William
        Participante.query.filter(Participante.id != william.id).delete()
        db.session.commit()
        print("Banco limpo com sucesso!")

        print("3. Criando campeonato oficial: Brasileirão 2025...")
        camp = Campeonato(nome="Brasileirão 2025", ano=2025)
        db.session.add(camp)
        db.session.commit()

        caminho_planilha = r"c:\Users\Arquivos\Downloads\William\Tabela de Pontuação do Bolão.xlsx"
        if not os.path.exists(caminho_planilha):
            print(f"ERRO: Arquivo não encontrado: {caminho_planilha}")
            return

        print(f"4. Carregando planilha oficial: {os.path.basename(caminho_planilha)}...")
        wb = openpyxl.load_workbook(caminho_planilha, data_only=True)

        padrao_jogo_com_placar = re.compile(r"^(.+?)\s+(\d+)\s*[xX]\s*(\d+)\s+(.+)$")
        padrao_jogo_sem_placar = re.compile(r"^(.+?)\s+[xX]\s+(.+)$")
        padrao_palpite = re.compile(r"(\d+)\s*[xX]\s*(\d+)")

        palavras_ignorar = [
            "pontua", "ponto", "cravada", "acerto", "total", "totais", "classificacao", "ranking"
        ]

        # Mapeamento de participantes: nome normalizado -> objeto Participante
        participantes_db = {william.nome.strip().lower(): william}

        # Filtra as abas que representam rodadas
        abas_rodadas = [s for s in wb.sheetnames if "rodada" in s.lower()]
        
        # Ordena as rodadas numericamente se possível (1º Rodada, 2º Rodada, ..., 38º Rodada)
        def extrair_num_rodada(nome):
            m = re.search(r"(\d+)", nome)
            return int(m.group(1)) if m else 999
        
        abas_rodadas.sort(key=extrair_num_rodada)
        print(f"Encontradas {len(abas_rodadas)} abas de rodadas.")

        total_jogos = 0
        total_palpites = 0
        total_resultados = 0

        for nome_aba in abas_rodadas:
            ws = wb[nome_aba]
            linhas = list(ws.iter_rows(values_only=True))
            if not linhas:
                continue

            num_rod = extrair_num_rodada(nome_aba)
            nome_rodada_formatado = f"{num_rod}ª Rodada" if num_rod != 999 else nome_aba.strip()

            rodada = Rodada(nome=nome_rodada_formatado, campeonato_id=camp.id, aberta=True)
            db.session.add(rodada)
            db.session.flush()

            # Linha 1 tem os participantes a partir da coluna B (índice 1)
            header = linhas[0]
            col_para_participante = {}

            for col_idx in range(1, len(header)):
                val = header[col_idx]
                if val is None:
                    continue
                nome_part = str(val).strip()
                if not nome_part or any(p in nome_part.lower() for p in palavras_ignorar):
                    continue

                part_key = nome_part.lower()
                if part_key not in participantes_db:
                    # Gera email amigável
                    slug = re.sub(r"[^a-zA-Z0-9]+", ".", nome_part.lower()).strip(".") or "user"
                    email = f"{slug}@bolao.local"
                    contador = 1
                    while Participante.query.filter_by(email=email).first():
                        email = f"{slug}{contador}@bolao.local"
                        contador += 1

                    novo_p = Participante(
                        nome=nome_part,
                        email=email,
                        senha=generate_password_hash("123456"),
                        admin=False,
                    )
                    db.session.add(novo_p)
                    db.session.flush()
                    participantes_db[part_key] = novo_p

                col_para_participante[col_idx] = participantes_db[part_key]

            # Linhas de jogos
            jogos_da_rodada_com_resultado = 0

            for idx in range(1, len(linhas)):
                col0 = linhas[idx][0]
                if not col0:
                    continue

                str_col0 = str(col0).strip()
                str_col0_lower = str_col0.lower()

                if any(p in str_col0_lower for p in palavras_ignorar):
                    continue

                # Identifica se é clássico (★ ou *)
                especial = "★" in str_col0 or "*" in str_col0
                str_limpa = str_col0.replace("★", "").replace("*", "").strip()

                m_com_placar = padrao_jogo_com_placar.match(str_limpa)
                m_sem_placar = padrao_jogo_sem_placar.match(str_limpa)

                time_casa = None
                time_fora = None
                gols_casa_real = None
                gols_fora_real = None

                if m_com_placar:
                    tc, gc, gf, tf = m_com_placar.groups()
                    time_casa = tc.strip()
                    time_fora = tf.strip()
                    gols_casa_real = int(gc)
                    gols_fora_real = int(gf)
                elif m_sem_placar:
                    tc, tf = m_sem_placar.groups()
                    time_casa = tc.strip()
                    time_fora = tf.strip()
                else:
                    continue

                tem_resultado = (gols_casa_real is not None and gols_fora_real is not None)

                jogo = Jogo(
                    rodada_id=rodada.id,
                    time_casa=time_casa,
                    time_fora=time_fora,
                    especial=especial,
                    encerrado=tem_resultado,
                )
                db.session.add(jogo)
                db.session.flush()
                total_jogos += 1

                if tem_resultado:
                    jogos_da_rodada_com_resultado += 1
                    res = Resultado(
                        jogo_id=jogo.id,
                        gols_casa_real=gols_casa_real,
                        gols_fora_real=gols_fora_real,
                    )
                    db.session.add(res)
                    total_resultados += 1

                # Palpites
                linha_atual = linhas[idx]
                for col_idx, part_obj in col_para_participante.items():
                    if col_idx < len(linha_atual):
                        val_palp = linha_atual[col_idx]
                        if val_palp is None:
                            continue
                        m_palp = padrao_palpite.search(str(val_palp))
                        if m_palp:
                            gc_p, gf_p = m_palp.groups()
                            palpite = Palpite(
                                participante_id=part_obj.id,
                                jogo_id=jogo.id,
                                gols_casa=int(gc_p),
                                gols_fora=int(gf_p),
                            )
                            db.session.add(palpite)
                            total_palpites += 1

            # Se todos os jogos da rodada já tiveram resultado, fecha a rodada para novos palpites
            if jogos_da_rodada_com_resultado > 0:
                rodada.aberta = False
            else:
                rodada.aberta = True

        db.session.commit()

        print("\n=== IMPORTAÇÃO CONCLUÍDA COM SUCESSO! ===")
        print(f"Campeonato: {camp.nome}")
        print(f"Total de Participantes: {Participante.query.count()}")
        print(f"Total de Rodadas: {Rodada.query.filter_by(campeonato_id=camp.id).count()}")
        print(f"Total de Jogos: {total_jogos}")
        print(f"Total de Resultados Oficiais: {total_resultados}")
        print(f"Total de Palpites Cadastrados: {total_palpites}")


if __name__ == "__main__":
    reset_e_importar()
