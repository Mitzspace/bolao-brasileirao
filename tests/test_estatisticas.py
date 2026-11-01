"""Possíveis ganhadores: simulação, situações do bolão, eliminação e acesso só pela gestão."""
import pytest

from database import db
from models import CorteEliminacao, Jogo, Palpite, Participacao, Resultado, Rodada
from services.estatisticas import possiveis_ganhadores
from tests.apoio import estrutura
from tests.test_interface import entrar, gestao  # noqa: F401


@pytest.fixture
def base(participante_teste, campeonato_teste):
    """Sem o responsável na disputa, para as contas ficarem só entre os participantes do cenário."""
    bolao, responsavel = estrutura(participante_teste, campeonato_teste, 'Bolão')
    responsavel.status = 'removido'
    db.session.commit()
    return bolao


def pessoa(bolao, nome, **campos):
    p = Participacao(bolao=bolao, nome_exibicao=nome, **campos)
    db.session.add(p)
    return p


def rodada(bolao, numero):
    r = Rodada(nome=f'Rodada {numero}', campeonato=bolao.campeonato)
    db.session.add(r)
    return r


def jogo_encerrado(r, palpites, placar=(1, 0), **campos):
    """palpites: {participação: (casa, fora)}; o placar real é `placar`."""
    j = Jogo(rodada=r, time_casa='A', time_fora='B', **campos)
    db.session.add(j)
    db.session.flush()
    db.session.add(Resultado(jogo=j, gols_casa_real=placar[0], gols_fora_real=placar[1]))
    for p, (casa, fora) in palpites.items():
        db.session.add(Palpite(participacao=p, jogo=j, gols_casa=casa, gols_fora=fora))
    return j


def jogos_futuros(r, quantos, **campos):
    lista = [Jogo(rodada=r, time_casa='C', time_fora='D', **campos) for _ in range(quantos)]
    db.session.add_all(lista)
    return lista


def por_nome(dados):
    return {l['nome']: l for l in dados['participantes']}


def cenario_disputado(bolao, futuros=10):
    """Ana cravou 8 de 10, Bia 3 de 10; Caio não acerta nada."""
    ana, bia, caio = pessoa(bolao, 'Ana'), pessoa(bolao, 'Bia'), pessoa(bolao, 'Caio')
    r1, r2 = rodada(bolao, 1), rodada(bolao, 2)
    for i in range(10):
        jogo_encerrado(r1, {ana: (1, 0) if i < 8 else (0, 1), bia: (1, 0) if i < 3 else (0, 1), caio: (0, 1)})
    jogos_futuros(r2, futuros)
    db.session.commit()
    return ana, bia, caio, r1, r2


def test_probabilidades_somam_100_e_favorecem_quem_acerta_mais(base):
    cenario_disputado(base)
    dados = possiveis_ganhadores(base)
    assert dados['situacao'] == 'simulada'
    assert dados['simulacoes'] >= 1000 and dados['jogosRestantes'] == 10 and dados['rodadasRestantes'] == 1
    linhas = por_nome(dados)
    assert sum(l['probabilidade'] for l in dados['participantes']) == pytest.approx(100, abs=0.2)
    assert linhas['Ana']['probabilidade'] > linhas['Bia']['probabilidade'] >= linhas['Caio']['probabilidade']
    assert dados['participantes'][0]['nome'] == 'Ana'
    assert linhas['Ana']['chancePodio'] == 100  # só três na disputa
    assert linhas['Ana']['pontosProjetados'] > linhas['Ana']['pontos']


def test_resultado_e_estavel_entre_recargas(base):
    cenario_disputado(base)
    assert possiveis_ganhadores(base) == possiveis_ganhadores(base)


def test_lider_com_folga_inalcancavel_e_quem_nao_alcanca_fica_sem_chance(base):
    ana, bia, _, _, _ = cenario_disputado(base, futuros=1)
    linhas = por_nome(possiveis_ganhadores(base))
    # Ana 24 pontos; 1 jogo vale no máximo 3 + 2 de bônus: Bia (9) e Caio (0) não alcançam.
    assert linhas['Ana']['probabilidade'] == 100
    assert linhas['Bia']['semChance'] and linhas['Caio']['semChance']
    assert linhas['Bia']['probabilidade'] == 0
    assert linhas['Bia']['pontosMaximos'] == 9 + 5
    assert linhas['Bia']['distanciaLider'] == 15


def test_desempate_final_segue_o_ranking(base):
    """Pontos iguais e nenhum jogo sorteado muda isso: vale cravadas, como na classificação."""
    ana, bia = pessoa(base, 'Ana'), pessoa(base, 'Bia')
    r1, r2 = rodada(base, 1), rodada(base, 2)
    jogo_encerrado(r1, {bia: (1, 0)}, placar=(1, 0))  # cravada: 3
    jogo_encerrado(r1, {ana: (2, 0)}, placar=(1, 0))  # resultado: 1
    jogo_encerrado(r1, {ana: (2, 0)}, placar=(1, 0))
    jogo_encerrado(r1, {ana: (2, 0)}, placar=(1, 0))
    jogos_futuros(r2, 1)
    db.session.commit()
    dados = possiveis_ganhadores(base)
    assert dados['participantes'][0]['pontos'] == 3
    # Empatadas em 3, Bia lidera pelo desempate e só perde nas simulações em que Ana pontua mais.
    assert por_nome(dados)['Bia']['posicao'] == 1


def test_desistente_fica_fora_e_entrada_tardia_disputa(base):
    ana, bia, _, r1, r2 = cenario_disputado(base)
    ana.status = 'desistente'
    ana.rodada_desistencia = r2
    tardia = pessoa(base, 'Dani', rodada_entrada=r2)
    db.session.commit()
    dados = possiveis_ganhadores(base)
    linhas = por_nome(dados)
    assert 'Ana' not in linhas and dados['desistentes'] == 1
    assert linhas['Bia']['posicao'] == 1  # a posição desconsidera quem saiu
    assert linhas['Dani']['desempenho']['jogos'] == 0 and linhas['Dani']['desempenho']['aproveitamento'] is None
    # Sem histórico, Dani usa o de colegas e pode pontuar nas rodadas em que já participa.
    assert linhas['Dani']['pontosProjetados'] > 0
    assert tardia.id == linhas['Dani']['participacaoId']


def test_participante_que_entra_depois_nao_pontua_antes(base):
    ana, _, _, _, r2 = cenario_disputado(base)
    r3 = rodada(base, 3)
    db.session.flush()
    pessoa(base, 'Dani', rodada_entrada=r3)  # só disputa a rodada 3, sem jogos
    db.session.commit()
    linhas = por_nome(possiveis_ganhadores(base))
    assert linhas['Dani']['pontosProjetados'] == 0 and linhas['Dani']['pontosMaximos'] == 0


@pytest.mark.parametrize('status, situacao, campeao', [('finalizado', 'encerrado', 100), ('desistido', 'desistido', None)])
def test_bolao_encerrado_nao_simula(base, status, situacao, campeao):
    cenario_disputado(base)
    base.status = status
    db.session.commit()
    dados = possiveis_ganhadores(base)
    assert dados['situacao'] == situacao and dados['simulacoes'] == 0
    assert por_nome(dados)['Ana']['probabilidade'] == campeao


def test_sem_jogos_restantes_o_lider_leva(base):
    cenario_disputado(base, futuros=0)
    dados = possiveis_ganhadores(base)
    assert dados['situacao'] == 'sem_jogos' and dados['simulacoes'] == 0
    assert dados['participantes'][0]['nome'] == 'Ana' and dados['participantes'][0]['probabilidade'] == 100
    assert por_nome(dados)['Bia']['probabilidade'] == 0


def test_sem_resultados_nao_estima(base):
    pessoa(base, 'Ana')
    jogos_futuros(rodada(base, 1), 3)
    db.session.commit()
    dados = possiveis_ganhadores(base)
    assert dados['situacao'] == 'sem_resultados'
    assert dados['participantes'][0]['probabilidade'] is None


def test_ninguem_pontuou_nao_elege_favorito_pelo_nome(base):
    ana, bia = pessoa(base, 'Ana'), pessoa(base, 'Bia')
    r1 = rodada(base, 1)
    jogo_encerrado(r1, {ana: (0, 1), bia: (0, 1)})
    jogos_futuros(rodada(base, 2), 2)
    db.session.commit()
    dados = possiveis_ganhadores(base)
    assert dados['situacao'] == 'sem_resultados'
    assert all(l['probabilidade'] is None for l in dados['participantes'])


def test_sem_participantes(base):
    jogos_futuros(rodada(base, 1), 1)
    db.session.commit()
    dados = possiveis_ganhadores(base)
    assert dados['situacao'] == 'sem_participantes' and dados['participantes'] == []


def test_poucos_jogos_avisa(base):
    ana = pessoa(base, 'Ana')
    r1 = rodada(base, 1)
    jogo_encerrado(r1, {ana: (1, 0)})
    jogos_futuros(rodada(base, 2), 2)
    db.session.commit()
    assert possiveis_ganhadores(base)['poucosDados'] is True


def test_corte_futuro_tira_da_disputa_quem_fica_fora(base):
    """Corte na rodada 2 deixa só 1: Bia nunca chega ao fim, mesmo com muitos jogos depois."""
    base.eliminacao_participantes = True
    ana, bia = pessoa(base, 'Ana'), pessoa(base, 'Bia')
    r1, r2, r3 = rodada(base, 1), rodada(base, 2), rodada(base, 3)
    for _ in range(5):
        jogo_encerrado(r1, {ana: (1, 0), bia: (0, 1)})
    r2_jogo = jogos_futuros(r2, 1)
    jogos_futuros(r3, 30)
    db.session.add(CorteEliminacao(bolao=base, rodada=r2, classificados=1))
    db.session.commit()
    assert r2_jogo
    linhas = por_nome(possiveis_ganhadores(base))
    assert linhas['Ana']['probabilidade'] == 100
    assert linhas['Bia']['probabilidade'] == 0
    # Sem o corte, 30 jogos deixariam Bia matematicamente viva: "sem chance" olha só os pontos.
    assert linhas['Bia']['semChance'] is False


def test_eliminado_em_corte_concluido_nao_aparece(base):
    base.eliminacao_participantes = True
    ana, bia = pessoa(base, 'Ana'), pessoa(base, 'Bia')
    r1, r2 = rodada(base, 1), rodada(base, 2)
    jogo_encerrado(r1, {ana: (1, 0), bia: (0, 1)})
    jogos_futuros(r2, 2)
    db.session.add(CorteEliminacao(bolao=base, rodada=r1, classificados=1))
    db.session.commit()
    dados = possiveis_ganhadores(base)
    assert dados['eliminados'] == 2 and list(por_nome(dados)) == ['Ana']  # Bia e o responsável removido


def test_pontos_de_penaltis_entram_no_mata_mata(base):
    base.pontos_penaltis_exato = 10
    ana = pessoa(base, 'Ana')
    r1, r2 = rodada(base, 1), rodada(base, 2)
    j = jogo_encerrado(r1, {}, placar=(1, 1), pode_penaltis=True)
    j.resultado.penaltis_casa_real, j.resultado.penaltis_fora_real = 4, 3
    db.session.add(Palpite(participacao=ana, jogo=j, gols_casa=1, gols_fora=1, penaltis_casa=4, penaltis_fora=3))
    jogos_futuros(r2, 1, pode_penaltis=True)
    db.session.commit()
    linha = por_nome(possiveis_ganhadores(base))['Ana']
    assert linha['pontos'] == 3 + 10
    assert linha['pontosProjetados'] == 2 * (3 + 10)
    assert linha['pontosMaximos'] == 13 + 3 + 2 + 10


def test_jogo_comum_nao_soma_penaltis_do_historico(base):
    base.pontos_penaltis_exato = 10
    ana = pessoa(base, 'Ana')
    r1, r2 = rodada(base, 1), rodada(base, 2)
    j = jogo_encerrado(r1, {}, placar=(1, 1), pode_penaltis=True)
    j.resultado.penaltis_casa_real, j.resultado.penaltis_fora_real = 4, 3
    db.session.add(Palpite(participacao=ana, jogo=j, gols_casa=1, gols_fora=1, penaltis_casa=4, penaltis_fora=3))
    jogos_futuros(r2, 1)
    db.session.commit()
    assert por_nome(possiveis_ganhadores(base))['Ana']['pontosProjetados'] == 13 + 3


def test_classico_futuro_usa_os_pontos_de_classico(base):
    ana = pessoa(base, 'Ana')
    r1, r2 = rodada(base, 1), rodada(base, 2)
    jogo_encerrado(r1, {ana: (1, 0)})
    jogos_futuros(r2, 1, classico=True)
    db.session.commit()
    assert por_nome(possiveis_ganhadores(base))['Ana']['pontosProjetados'] == 3 + 5


def test_desempenho(base):
    ana, _, _, r1, _ = cenario_disputado(base)
    linha = por_nome(possiveis_ganhadores(base))['Ana']
    d = linha['desempenho']
    assert d['jogos'] == 10 and d['aproveitamento'] == 80
    assert d['mediaPorJogo'] == 2.4 and d['mediaRecente'] == 2.4
    assert d['melhorRodada'] == {'nome': r1.nome, 'pontos': 24}


# ---------- rotas ----------

def test_api_gestao(client, gestao_estatisticas):
    usuario, bolao = gestao_estatisticas
    assert client.get('/interface/api/estatisticas').status_code == 401
    entrar(client, usuario)
    client.post('/interface/selecionar', data={'bolao_id': bolao.id})
    resposta = client.get('/interface/api/estatisticas')
    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert dados['situacao'] == 'simulada'
    assert {'Ana', 'Bia', 'Caio'} <= set(por_nome(dados))
    assert dados['bolao']['status'] == 'ativo'


@pytest.mark.parametrize('view', ['tabela', 'estatisticas'])
def test_escolher_bolao_abre_a_aba_pedida(client, gestao_estatisticas, view):
    usuario, bolao = gestao_estatisticas
    entrar(client, usuario)
    resposta = client.post('/interface/selecionar', data={'bolao_id': bolao.id, 'view': view})
    assert resposta.location.endswith(f'/interface/#{view}')


def test_area_publica_nao_tem_estatisticas(client, base):
    _, _, _, r1, _ = cenario_disputado(base)
    base.codigo_publico = 'e' * 20
    base.rodada_publica = r1
    db.session.commit()
    assert client.get(f'/publico/{base.codigo_publico}/api/estatisticas').status_code == 404


@pytest.fixture
def gestao_estatisticas(gestao):
    usuario, boloes = gestao
    cenario_disputado(boloes[0])
    return usuario, boloes[0]

