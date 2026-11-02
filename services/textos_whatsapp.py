"""Textos de gestão sem dados de conta, usando os pontos já calculados."""
from services.pontuacao import texto_penaltis


def linha(valor):
    return ' '.join(str(valor or '').split())


def cabecalho(bolao, titulo):
    return [f'*{linha(bolao.nome)} — {titulo}*',
            f'{linha(bolao.campeonato.nome)} · Temporada {bolao.campeonato.ano or "não informada"}', '']


# Faixas do texto de classificação para o WhatsApp, proporcionais ao número de participantes
# (modelo do bolão com 20 pessoas: 4 verdes, 1 amarelo, 5 azuis, os demais brancos e 4 vermelhos).
PROPORCAO_VERDE = 0.20
PROPORCAO_AMARELO = 0.05
PROPORCAO_AZUL = 0.25
PROPORCAO_VERMELHO = 0.20


def _arredondar(valor):
    return int(valor + 0.5)  # meio para cima (round() do Python arredonda 2,5 para 2)


def faixas_compartilhar(total):
    """Quantidade de posições de cada cor: (verdes, amarelos, azuis, vermelhos).

    Verde e amarelo têm ao menos uma posição; as faixas do topo têm prioridade
    sobre o vermelho quando há poucos participantes.
    """
    if total <= 0:
        return 0, 0, 0, 0
    verdes = min(total, max(1, _arredondar(total * PROPORCAO_VERDE)))
    amarelos = min(total - verdes, max(1, _arredondar(total * PROPORCAO_AMARELO)))
    azuis = min(total - verdes - amarelos, _arredondar(total * PROPORCAO_AZUL))
    vermelhos = min(total - verdes - amarelos - azuis, _arredondar(total * PROPORCAO_VERMELHO))
    return verdes, amarelos, azuis, vermelhos


def marcador_posicao(posicao, total):
    verdes, amarelos, azuis, vermelhos = faixas_compartilhar(total)
    if posicao <= verdes:
        return '🟩'
    if posicao <= verdes + amarelos:
        return '🟨'
    if posicao <= verdes + amarelos + azuis:
        return '🟦'
    if posicao > total - vermelhos:
        return '🟥'
    return '⬜'


def _faixa(inicio, fim):
    return f'{inicio}º' if inicio == fim else f'{inicio}º ao {fim}º'


def legenda_compartilhar(total):
    """Legenda das cores para o total de participantes: [(marcador, faixa), ...] só das cores usadas."""
    verdes, amarelos, azuis, vermelhos = faixas_compartilhar(total)
    legenda, inicio = [], 1
    for marcador, quantidade in (('🟩', verdes), ('🟨', amarelos), ('🟦', azuis)):
        if quantidade:
            legenda.append((marcador, _faixa(inicio, inicio + quantidade - 1)))
            inicio += quantidade
    fim_brancos = total - vermelhos
    if fim_brancos >= inicio:
        legenda.append(('⬜', _faixa(inicio, fim_brancos)))
    if vermelhos:
        legenda.append(('🟥', _faixa(fim_brancos + 1, total)))
    return legenda


def texto_classificacao_compartilhar(bolao, ranking, rodada=None):
    """Texto curto da classificação, no modelo usado no grupo do bolão."""
    titulo = f'*🏆{linha(bolao.nome)}' + (f' · {linha(rodada.nome)}' if rodada else '') + '*'
    linhas = [titulo, '']
    total = len(ranking)
    for posicao, item in enumerate(ranking, 1):
        pontos = item['pontos']
        linhas.append(f"{marcador_posicao(posicao, total)} {posicao}. {linha(item['participante'].nome)} – "
                      f"{pontos} {'ponto' if pontos == 1 else 'pontos'}")
    if not ranking:
        linhas.append('Nenhum participante na classificação.')
    return '\n'.join(linhas)


def texto_rodada(bolao, rodada, matriz, participantes, totais):
    linhas = cabecalho(bolao, f'Resumo · {linha(rodada.nome)}')
    for item in matriz:
        jogo, resultado = item['jogo'], item['resultado']
        if resultado is None:
            linhas.append(f'{linha(jogo.time_casa)} × {linha(jogo.time_fora)} — aguardando resultado')
            linhas.append('')
            continue
        linhas.append(f'*{linha(jogo.time_casa)} {resultado.gols_casa_real} × '
                      f'{resultado.gols_fora_real} {linha(jogo.time_fora)}*'
                      + texto_penaltis(resultado.penaltis_casa_real, resultado.penaltis_fora_real, ' × ')
                      + (' · clássico' if jogo.classico else ''))
        if jogo.primeiro_marcador:
            linhas.append(f'Primeiro gol: {linha(jogo.primeiro_marcador)}')
        for pessoa in participantes:
            detalhe = item['palpites'][pessoa.id]
            palpite = detalhe['palpite']
            if palpite is not None and palpite.situacao != 'valido':
                linhas.append(f'• {linha(pessoa.nome)}: {palpite.situacao_label}')
                continue
            if palpite is None:
                linhas.append(f'• {linha(pessoa.nome)}: sem palpite')
            else:
                marcador = f' · 1º gol: {linha(palpite.primeiro_gol)}' if palpite.primeiro_gol else ''
                linhas.append(f'• {linha(pessoa.nome)}: {palpite.gols_casa} × {palpite.gols_fora}'
                              f'{texto_penaltis(palpite.penaltis_casa, palpite.penaltis_fora, " × ")}{marcador} → {detalhe["pontos"] or 0} pts')
        linhas.append('')
    if not matriz:
        linhas.extend(['Nenhum jogo cadastrado nesta rodada.', ''])
    linhas.append('*Totais da rodada*')
    for pessoa in participantes:
        total = totais[pessoa.id]
        linhas.append(f'• {linha(pessoa.nome)}: {total["pontos"]} pts '
                      f'(créditos históricos: {total.get("bonus", 0)}, já incluídos)')
    linhas.extend(['', 'Pontuação conforme os resultados registrados. Palpites de jogos sem resultado não são exibidos.'])
    return '\n'.join(linhas)
