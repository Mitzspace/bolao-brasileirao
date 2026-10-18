import unicodedata
from dataclasses import dataclass
from services.regras_pontuacao import REGRAS_PONTUACAO, regras_do_palpite


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
    # Disputa de pênaltis: soma ao total, mas não conta como cravada nem acerto de resultado.
    pontos_penaltis: int = 0
    penaltis_exato: bool = False
    penaltis_vencedor: bool = False

    @property
    def total(self):
        return self.pontos_placar + self.pontos_bonus + self.pontos_penaltis


def texto_penaltis(casa, fora, separador='x'):
    """Sufixo de exibição do placar dos pênaltis, ex.: " (pên. 4x3)"; vazio sem pênaltis."""
    if casa is None or fora is None:
        return ''
    return f' (pên. {casa}{separador}{fora})'


def _sinal(casa, fora):
    return (casa > fora) - (casa < fora)


def pontuar_penaltis(palpite, resultado, regras):
    """(pontos, exato, vencedor) do palpite dos pênaltis.

    Só pontua se o jogo real teve pênaltis e o palpite de pênaltis foi informado.
    """
    pc, pf = getattr(palpite, "penaltis_casa", None), getattr(palpite, "penaltis_fora", None)
    rc, rf = getattr(resultado, "penaltis_casa_real", None), getattr(resultado, "penaltis_fora_real", None)
    if None in (pc, pf, rc, rf):
        return 0, False, False
    if (pc, pf) == (rc, rf):
        return regras.get("penaltis_exato", REGRAS_PONTUACAO["penaltis_exato"]), True, True
    # Empate nos pênaltis não existe no jogo real; um palpite empatado só pontua se exato.
    if _sinal(pc, pf) != 0 and _sinal(pc, pf) == _sinal(rc, rf):
        return regras.get("penaltis_vencedor", REGRAS_PONTUACAO["penaltis_vencedor"]), False, True
    return 0, False, False


def calcular_pontuacao(palpite, jogo, resultado, regras=None):
    """Bônus independente do placar, inclusive gol contra; nunca em 0x0.

    regras: valores a usar; por padrão, as regras do bolão do palpite (ou as padrão).
    """
    if getattr(palpite, "situacao", "valido") in {"nao_enviado", "fora_prazo"}:
        return Pontuacao()
    if resultado is None or resultado.gols_casa_real is None or resultado.gols_fora_real is None:
        return Pontuacao()
    gc, gf = resultado.gols_casa_real, resultado.gols_fora_real
    pc, pf = palpite.gols_casa, palpite.gols_fora
    exato = (pc, pf) == (gc, gf)
    acerto = _sinal(pc, pf) == _sinal(gc, gf)
    regras = regras or regras_do_palpite(palpite)
    modo = "classico" if jogo.classico else "comum"
    placar = regras[f"{modo}_exato"] if exato else (
        regras[f"{modo}_resultado"] if acerto else 0)
    previsto = normalizar_nome_jogador(palpite.primeiro_gol)
    oficial = normalizar_nome_jogador(jogo.primeiro_marcador)
    bonus = regras["primeiro_gol"] if gc + gf > 0 and previsto and oficial and previsto == oficial else 0
    penaltis, pen_exato, pen_vencedor = pontuar_penaltis(palpite, resultado, regras)
    return Pontuacao(placar, bonus, exato, acerto, penaltis, pen_exato, pen_vencedor)
