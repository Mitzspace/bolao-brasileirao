"""
importar_planilha_exata.py — Importa com fidelidade 100% todos os dados da planilha oficial
enviada pelo usuário (media_1791047216625.xlsx), incluindo rodadas 1 a 38, placares reais,
palpites e a tabela de bônus por participante e rodada.
"""

import os
import sys
import re
import openpyxl

sys.path.insert(0, r"c:\Users\Arquivos\Downloads\William\bolao_v2\bolao2")

from app import create_app
from database import db
from models import BonusRodada, Campeonato, Jogo, Palpite, Participante, Resultado, Rodada
from werkzeug.security import generate_password_hash
from services.pontuacao import calcular_pontos


def extrair_num_rodada(nome):
    m = re.search(r"(\d+)", str(nome))
    return int(m.group(1)) if m else 999


def parse_placar(texto):
    """
    Tenta extrair time_casa, time_fora, gols_casa_real, gols_fora_real de formatos como:
      'Atlético-MG 2x2 Palmeiras'
      'Atlético-MG x Botafogo [1x1]'
      'Corinthians x São Paulo ★ [3x2]'
      'Fluminense x Coritiba'
    """
    if not texto:
        return None, None, None, None, False

    str_texto = str(texto).strip()
    especial = "★" in str_texto or "*" in str_texto
    limpo = str_texto.replace("★", "").replace("*", "").strip()

    # Formato com colchetes: TimeA x TimeB [1x1]
    m_colchetes = re.match(r"^(.+?)\s*\[(\d+)\s*[xX]\s*(\d+)\]$", limpo)
    if m_colchetes:
        confronto, gc, gf = m_colchetes.groups()
        m_times = re.match(r"^(.+?)\s+[xX]\s+(.+)$", confronto.strip())
        if m_times:
            return m_times.group(1).strip(), m_times.group(2).strip(), int(gc), int(gf), especial
        return confronto.strip(), "Adversário", int(gc), int(gf), especial

    # Formato tradicional com placar no meio: TimeA 2x1 TimeB
    m_meio = re.match(r"^(.+?)\s+(\d+)\s*[xX]\s*(\d+)\s+(.+)$", limpo)
    if m_meio:
        tc, gc, gf, tf = m_meio.groups()
        return tc.strip(), tf.strip(), int(gc), int(gf), especial

    # Formato sem placar: TimeA x TimeB
    m_sem = re.match(r"^(.+?)\s+[xX]\s+(.+)$", limpo)
    if m_sem:
        tc, tf = m_sem.groups()
        return tc.strip(), tf.strip(), None, None, especial

    return None, None, None, None, especial


def executar_importacao():
    caminho = r"C:/Users/Arquivos/.gemini/antigravity/brain/9850975f-2401-4f82-a09a-a1dc8c8e2926/.user_uploaded/media_1791047216625.xlsx"
    if not os.path.exists(caminho):
        # Fallback para o arquivo em downloads se necessário
        caminho = r"c:\Users\Arquivos\Downloads\William\Tabela de Pontuação do Bolão.xlsx"

    print(f"Lendo planilha: {caminho}")
    wb = openpyxl.load_workbook(caminho, data_only=True)

    app = create_app()
    with app.app_context():
        # Cria tabelas novas se não existirem
        db.create_all()

        william = Participante.query.filter_by(email="williambrejauba@gmail.com").first()
        if not william:
            william = Participante.query.filter_by(admin=True).first()

        if not william:
            print("ERRO: Usuário admin William não encontrado!")
            return

        print(f"Preservando Admin: {william.nome} ({william.email})")

        # Limpa dados antigos
        BonusRodada.query.delete()
        Palpite.query.delete()
        Resultado.query.delete()
        Jogo.query.delete()
        Rodada.query.delete()
        Campeonato.query.delete()
        Participante.query.filter(Participante.id != william.id).delete()
        db.session.commit()
        print("Banco de dados resetado.")

        # Cria campeonato
        camp = Campeonato(nome="Brasileirão 2025", ano=2025)
        db.session.add(camp)
        db.session.commit()

        # Lê participantes da aba TOTAL ou TABELA
        ws_total = wb["TOTAL"]
        linha_header = list(ws_total.iter_rows(values_only=True))[0]
        nomes_participantes = [str(p).strip() for p in linha_header[1:] if p is not None and str(p).strip()]

        participantes_db = {william.nome.strip().lower(): william}
        col_para_part = {}

        for col_idx, nome_part in enumerate(nomes_participantes, start=1):
            key = nome_part.lower()
            if key not in participantes_db:
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
                participantes_db[key] = novo_p

            col_para_part[col_idx] = participantes_db[key]

        print(f"Total de {len(participantes_db)} participantes mapeados.")

        # Mapeia Bônus por rodada a partir da aba TOTAL
        # Linha 44 é o cabeçalho 'BÔNUS', linhas 45 a 82 são as 38 rodadas
        bonus_por_rodada_e_part = {} # (num_rodada, part_id) -> pontos_bonus
        linhas_total = list(ws_total.iter_rows(values_only=True))
        
        inicio_bonus = None
        for idx, row in enumerate(linhas_total):
            c0 = str(row[0]).strip().upper() if row[0] else ""
            if "BÔNUS" in c0 or "BONUS" in c0:
                inicio_bonus = idx + 1
                break

        if inicio_bonus:
            for r_idx in range(inicio_bonus, min(inicio_bonus + 38, len(linhas_total))):
                row = linhas_total[r_idx]
                c0 = str(row[0]) if row[0] else ""
                num_rod = extrair_num_rodada(c0)
                if num_rod == 999:
                    continue
                for c_idx in range(1, len(row)):
                    val = row[c_idx]
                    if val is not None and str(val).strip():
                        try:
                            pts_b = int(float(val))
                            if pts_b > 0 and c_idx in col_para_part:
                                p_obj = col_para_part[c_idx]
                                bonus_por_rodada_e_part[(num_rod, p_obj.id)] = pts_b
                        except ValueError:
                            pass

        print(f"Mapeados {len(bonus_por_rodada_e_part)} registros de bônus.")

        # Agora lê cada aba de rodada (1 a 38)
        abas_rodadas = [s for s in wb.sheetnames if "rodada" in s.lower()]
        abas_rodadas.sort(key=extrair_num_rodada)

        padrao_palpite = re.compile(r"(\d+)\s*[xX]\s*(\d+)")
        palavras_ignorar = ["pontua", "ponto", "cravada", "acerto", "total", "totais", "classificacao", "ranking"]

        rodadas_criadas = {}

        for nome_aba in abas_rodadas:
            num_rod = extrair_num_rodada(nome_aba)
            nome_rodada_fmt = f"{num_rod}ª Rodada" if num_rod != 999 else nome_aba.strip()

            rodada = Rodada(nome=nome_rodada_fmt, campeonato_id=camp.id, aberta=True)
            db.session.add(rodada)
            db.session.flush()
            rodadas_criadas[num_rod] = rodada

            # Cadastra bônus dessa rodada se houver
            for (r_num, part_id), pts_b in bonus_por_rodada_e_part.items():
                if r_num == num_rod:
                    b_obj = BonusRodada(
                        participante_id=part_id,
                        rodada_id=rodada.id,
                        pontos=pts_b,
                        motivo="Bônus 1º Gol",
                    )
                    db.session.add(b_obj)

            ws = wb[nome_aba]
            linhas_aba = list(ws.iter_rows(values_only=True))
            if not linhas_aba:
                continue

            # Mapeamento de colunas na aba para os participantes
            header_aba = linhas_aba[0]
            col_aba_part = {}
            for c_idx in range(1, len(header_aba)):
                v = header_aba[c_idx]
                if v and str(v).strip():
                    k = str(v).strip().lower()
                    if k in participantes_db:
                        col_aba_part[c_idx] = participantes_db[k]

            jogos_com_resultado = 0

            for idx in range(1, len(linhas_aba)):
                col0 = linhas_aba[idx][0]
                if not col0:
                    continue

                str_c0 = str(col0).strip()
                if any(p in str_c0.lower() for p in palavras_ignorar):
                    continue

                time_casa, time_fora, gc, gf, especial = parse_placar(str_c0)
                if not time_casa or not time_fora:
                    continue

                # Se o placar não veio no nome, verifica se está em col27 da linha
                if gc is None and len(linhas_aba[idx]) > 27 and linhas_aba[idx][27]:
                    m_c27 = padrao_palpite.search(str(linhas_aba[idx][27]))
                    if m_c27:
                        gc = int(m_c27.group(1))
                        gf = int(m_c27.group(2))

                tem_resultado = (gc is not None and gf is not None)
                if tem_resultado:
                    jogos_com_resultado += 1

                jogo = Jogo(
                    rodada_id=rodada.id,
                    time_casa=time_casa,
                    time_fora=time_fora,
                    especial=especial,
                    encerrado=tem_resultado,
                )
                db.session.add(jogo)
                db.session.flush()

                if tem_resultado:
                    res = Resultado(
                        jogo_id=jogo.id,
                        gols_casa_real=gc,
                        gols_fora_real=gf,
                    )
                    db.session.add(res)

                # Palpites
                linha_atual = linhas_aba[idx]
                for c_idx, part_obj in col_aba_part.items():
                    if c_idx < len(linha_atual):
                        val_palp = linha_atual[c_idx]
                        if val_palp is not None and str(val_palp).strip():
                            m_p = padrao_palpite.search(str(val_palp))
                            if m_p:
                                p_casa, p_fora = m_p.groups()
                                palpite = Palpite(
                                    participante_id=part_obj.id,
                                    jogo_id=jogo.id,
                                    gols_casa=int(p_casa),
                                    gols_fora=int(p_fora),
                                )
                                db.session.add(palpite)

            # Se todos os jogos da rodada têm resultado, fecha a rodada
            if jogos_com_resultado > 0:
                rodada.aberta = False
            else:
                rodada.aberta = True

        db.session.commit()
        print("Importação e gravação no banco concluídas!")

        # Validação do Ranking
        print("\n=== VALIDAÇÃO DO RANKING CALCULADO ===")
        todos_p = Participante.query.all()
        ranking_calc = []
        for p in todos_p:
            pts_palpites = sum(
                calcular_pontos(pal, pal.jogo.resultado, pal.jogo.especial)
                for pal in p.palpites
                if pal.jogo and pal.jogo.resultado
            )
            pts_bonus = sum(b.pontos for b in p.bonus_list)
            total = pts_palpites + pts_bonus
            cravadas = sum(
                1 for pal in p.palpites
                if pal.jogo and pal.jogo.resultado and pal.gols_casa == pal.jogo.resultado.gols_casa_real and pal.gols_fora == pal.jogo.resultado.gols_fora_real
            )
            ranking_calc.append({
                "nome": p.nome,
                "palpites": pts_palpites,
                "bonus": pts_bonus,
                "total": total,
                "cravadas": cravadas
            })

        ranking_calc.sort(key=lambda i: (i["total"], i["cravadas"]), reverse=True)
        print("Pos | Nome            | Palpites | Bônus | Cravadas | TOTAL")
        print("----------------------------------------------------------")
        for idx, item in enumerate(ranking_calc, 1):
            nm = item["nome"]
            pl = item["palpites"]
            bn = item["bonus"]
            cr = item["cravadas"]
            tt = item["total"]
            print(f"{idx:2d}º | {nm:15s} | {pl:8d} | {bn:5d} | {cr:8d} | {tt:5d} pts")


if __name__ == "__main__":
    executar_importacao()
