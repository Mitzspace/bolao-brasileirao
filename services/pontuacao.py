import unicodedata
from dataclasses import dataclass
from types import SimpleNamespace
from services.regras_pontuacao import REGRAS_PONTUACAO


def normalizar_nome_jogador(valor):
    if not valor:
        return ""

    sem_acentos = unicodedata.normalize("NFKD", valor)
    sem_acentos = "".join(c for c in sem_acentos if not unicodedata.combining(c))
    return " ".join(sem_acentos.casefold().split())


@dataclass(frozen=True)
class Pontuacao:
    pontos_placar: int = 0
    pontos_bonus: int = 0
    placar_exato: bool = False
    acertou_resultado: bool = False

    @property
    def total(self):
        return self.pontos_placar + self.pontos_bonus


def calcular_pontuacao(palpite, jogo, resultado):
    """Bônus independente do placar, inclusive gol contra; nunca em 0x0."""
    if getattr(palpite, "situacao", "valido") in {"nao_enviado", "fora_prazo"}:
        return Pontuacao()
    if resultado is None or resultado.gols_casa_real is None or resultado.gols_fora_real is None:
        return Pontuacao()
    gc, gf = resultado.gols_casa_real, resultado.gols_fora_real
    pc, pf = palpite.gols_casa, palpite.gols_fora
    exato = (pc, pf) == (gc, gf)
    acerto = ((pc > pf) - (pc < pf)) == ((gc > gf) - (gc < gf))
    modo = "classico" if jogo.classico else "comum"
    placar = REGRAS_PONTUACAO[f"{modo}_exato"] if exato else (
        REGRAS_PONTUACAO[f"{modo}_resultado"] if acerto else 0)
    previsto = normalizar_nome_jogador(palpite.primeiro_gol)
    oficial = normalizar_nome_jogador(jogo.primeiro_marcador)
    bonus = REGRAS_PONTUACAO["primeiro_gol"] if gc + gf > 0 and previsto and oficial and previsto == oficial else 0
    return Pontuacao(placar, bonus, exato, acerto)


def calcular_pontos(palpite, resultado, especial=False):
    """Adaptador dos scripts antigos; a função principal recebe palpite, jogo e resultado."""
    jogo = SimpleNamespace(classico=especial, primeiro_marcador=resultado.primeiro_gol_real)
    return calcular_pontuacao(palpite, jogo, resultado).total
