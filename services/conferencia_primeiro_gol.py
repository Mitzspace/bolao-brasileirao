"""Conferência dos bônus de primeiro gol já disputados (python -m scripts.conferir_primeiro_gol).

Os bônus vindos da planilha ficaram como créditos por rodada (BonusRodada), sem dizer qual jogo
foi acertado. A conferência:
1. preenche, com a ESPN, o primeiro marcador dos clássicos encerrados que estão sem ele
   (o que já foi digitado é mantido; só é comparado com a ESPN para aviso);
2. recalcula, palpite a palpite, o bônus de cada participação em cada rodada;
3. compara com o crédito histórico da rodada e classifica:
   - confere: o recalculado é igual ao crédito -> o crédito vira bônus por jogo (zera);
   - planilha_maior: a planilha deu mais do que os palpites explicam -> sobra só a diferença;
   - planilha_menor: os palpites justificam mais do que a planilha deu -> o total sobe;
   - sem_palpite_1g: crédito numa rodada sem palpite de primeiro gol no sistema -> intocado;
   - bonus_novo: rodada sem crédito em que o marcador preenchido gera bônus novo.
Nada é gravado sem aplicar(); o relatório mostra antes a variação de pontos de cada pessoa.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from types import SimpleNamespace

from sqlalchemy.orm import joinedload, selectinload

from services.pontuacao import _palavras_jogador, calcular_pontuacao, mesmo_jogador
from services.primeiro_gol import (_juntar, avaliar_jogo, buscar_eventos, evento_do_jogo,
                                   gravar_primeiro_marcador, jogos_sem_marcador, marcador_vazio)

DESCRICAO_JOGO = {
    "encontrado": "Preenchido pela ESPN",
    "ja_preenchido": "Já estava digitado",
    "digitado_diferente": "Digitado difere da ESPN (mantido)",
    "sem_gols": "Jogo sem gols",
    "nao_encontrado": "Jogo não encontrado na ESPN",
    "placar_diferente": "Placar da ESPN difere do lançado",
    "sem_lances": "ESPN sem lances do jogo",
    "sem_nome": "ESPN sem o nome do autor",
}
DESCRICAO_PESSOA = {
    "confere": "Planilha confere com os palpites",
    "planilha_maior": "Planilha deu mais bônus do que os palpites explicam",
    "planilha_menor": "Palpites justificam mais bônus do que a planilha deu",
    "sem_palpite_1g": "Crédito sem palpite de 1º gol no sistema",
    "bonus_novo": "Bônus novo pelo marcador preenchido",
}


@dataclass
class Relatorio:
    bolao: object
    jogos: list = field(default_factory=list)
    pessoas: list = field(default_factory=list)
    quase: list = field(default_factory=list)


def eventos_para_conferencia(campeonato, liga):
    """Temporada inteira da ESPN numa consulta; dias avulsos para os jogos que vieram sem lances."""
    eventos = buscar_eventos(liga, temporada=campeonato.ano) if campeonato.ano else []
    dias = set()
    for jogo in jogos_sem_marcador(campeonato.id):
        evento = evento_do_jogo(jogo, eventos)
        data = (evento or {}).get("data") or jogo.data
        if data and (evento is None or not evento["tem_detalhes"]):
            dias.update({data.date(), data.date() - timedelta(days=1)})
    return _juntar(eventos, buscar_eventos(liga, dias=dias)) if dias else eventos


def quase_acerto(previsto, oficial):
    """Palpite que não pontua pela regra, mas tem um nome em comum com o oficial (para revisão)."""
    if not previsto or not oficial or mesmo_jogador(previsto, oficial):
        return False
    a = {p for p in _palavras_jogador(previsto) if len(p) >= 4}
    return bool(a & {p for p in _palavras_jogador(oficial) if len(p) >= 4})


def conferir(bolao, eventos):
    from models import Jogo, Participacao, Rodada
    from services.contexto_bolao import ordem_rodada
    from services.elegibilidade import dentro_do_periodo, palpite_elegivel
    from services.regras_pontuacao import regras_do_bolao

    regras = regras_do_bolao(bolao)
    relatorio = Relatorio(bolao)
    jogos = [j for j in Jogo.query.join(Rodada, Rodada.id == Jogo.rodada_id)
             .filter(Rodada.campeonato_id == bolao.campeonato_id, Jogo.classico.is_(True))
             .options(joinedload(Jogo.resultado), joinedload(Jogo.rodada)).all() if j.resultado is not None]
    jogos.sort(key=lambda j: (ordem_rodada(j.rodada), j.data is None, j.data or 0, j.id))

    marcador = {}
    for jogo in jogos:
        atual = (jogo.primeiro_marcador or "").strip() or None
        gols = (jogo.resultado.gols_casa_real or 0) + (jogo.resultado.gols_fora_real or 0)
        espn = None
        if gols == 0:
            situacao = "sem_gols"
        else:
            situacao, espn, _ = avaliar_jogo(jogo, eventos)
            if atual:
                situacao = ("digitado_diferente" if situacao == "encontrado" and not mesmo_jogador(atual, espn)
                            else "ja_preenchido")
        marcador[jogo.id] = atual or (espn if situacao == "encontrado" else None)
        relatorio.jogos.append({"jogo": jogo, "marcador_atual": atual, "marcador_espn": espn,
                                "situacao": situacao})

    por_id = {j.id: j for j in jogos}
    participacoes = (Participacao.query.filter_by(bolao_id=bolao.id)
                     .options(selectinload(Participacao.palpites),
                              selectinload(Participacao.creditos_historicos)).all())
    for part in participacoes:
        rodadas = defaultdict(lambda: {"atual": 0, "novo": 0, "com_palpite": False, "acertos": []})
        for pal in part.palpites:
            jogo = por_id.get(pal.jogo_id)
            if jogo is None or not palpite_elegivel(pal):
                continue
            dados = rodadas[jogo.rodada_id]
            previsto = (pal.primeiro_gol or "").strip()
            dados["com_palpite"] = dados["com_palpite"] or bool(previsto)
            dados["atual"] += calcular_pontuacao(pal, jogo, jogo.resultado, regras).pontos_bonus
            simulado = SimpleNamespace(classico=jogo.classico, primeiro_marcador=marcador[jogo.id])
            novo = calcular_pontuacao(pal, simulado, jogo.resultado, regras).pontos_bonus
            dados["novo"] += novo
            if novo:
                dados["acertos"].append(f"{jogo.time_casa} x {jogo.time_fora} ({previsto})")
            elif quase_acerto(previsto, marcador[jogo.id]):
                relatorio.quase.append({"participacao": part, "jogo": jogo, "palpite": previsto,
                                        "oficial": marcador[jogo.id]})

        creditos = {b.rodada_id: b for b in part.creditos_historicos}
        for rodada_id in set(rodadas) | set(creditos):
            credito_obj = creditos.get(rodada_id)
            if credito_obj is not None and not dentro_do_periodo(part, credito_obj.rodada):
                continue  # fora do período: o ranking já ignora este crédito
            dados = rodadas.get(rodada_id) or {"atual": 0, "novo": 0, "com_palpite": False, "acertos": []}
            credito = credito_obj.pontos if credito_obj else 0
            if credito:
                if not dados["com_palpite"] and dados["novo"] == 0:
                    situacao, credito_novo = "sem_palpite_1g", credito
                elif dados["novo"] == credito:
                    situacao, credito_novo = "confere", 0
                elif dados["novo"] < credito:
                    situacao, credito_novo = "planilha_maior", credito - dados["novo"]
                else:
                    situacao, credito_novo = "planilha_menor", 0
            elif dados["novo"] != dados["atual"]:
                situacao, credito_novo = "bonus_novo", 0
            else:
                continue
            rodada = credito_obj.rodada if credito_obj else por_id_rodada(jogos, rodada_id)
            relatorio.pessoas.append({
                "participacao": part, "rodada": rodada, "credito": credito, "credito_obj": credito_obj,
                "bonus_atual": dados["atual"], "bonus_novo": dados["novo"], "credito_novo": credito_novo,
                "variacao": (dados["novo"] + credito_novo) - (dados["atual"] + credito),
                "situacao": situacao, "acertos": dados["acertos"],
                "nao_multiplo": bool(credito and regras["primeiro_gol"] and credito % regras["primeiro_gol"]),
            })
    relatorio.pessoas.sort(key=lambda p: (ordem_rodada(p["rodada"]), p["participacao"].nome_exibicao.casefold()))
    return relatorio


def por_id_rodada(jogos, rodada_id):
    return next(j.rodada for j in jogos if j.rodada_id == rodada_id)


def aplicar(relatorio, data_texto):
    """Grava os marcadores encontrados e ajusta os créditos históricos (sem commit)."""
    preenchidos = ajustados = 0
    for linha in relatorio.jogos:
        jogo = linha["jogo"]
        if (linha["situacao"] == "encontrado" and marcador_vazio(jogo)
                and gravar_primeiro_marcador(jogo, jogo.resultado, linha["marcador_espn"])):
            preenchidos += 1
    for linha in relatorio.pessoas:
        credito = linha["credito_obj"]
        if credito is not None and linha["credito_novo"] != credito.pontos:
            credito.pontos = linha["credito_novo"]
            credito.motivo = f"Bônus histórico conferido em {data_texto}"[:100]
            ajustados += 1
    return preenchidos, ajustados
