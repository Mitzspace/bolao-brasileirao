"""Textos de gestão sem dados de conta, usando os pontos já calculados."""


def linha(valor):
    return ' '.join(str(valor or '').split())


def cabecalho(bolao, titulo):
    return [f'*{linha(bolao.nome)} — {titulo}*',
            f'{linha(bolao.campeonato.nome)} · Temporada {bolao.campeonato.ano or "não informada"}', '']


# Faixas do texto de classificação para o WhatsApp (modelo do bolão):
# 1º–4º verde, 5º amarelo, 6º–10º azul, últimos 4 vermelho e o restante branco.
FAIXAS_COMPARTILHAR = ((1, 4, '🟩'), (5, 5, '🟨'), (6, 10, '🟦'))
ULTIMOS_VERMELHOS = 4
ULTIMA_POSICAO_PROTEGIDA = 10  # as faixas do topo têm prioridade sobre o vermelho


def marcador_posicao(posicao, total):
    for inicio, fim, marcador in FAIXAS_COMPARTILHAR:
        if inicio <= posicao <= fim:
            return marcador
    if posicao > ULTIMA_POSICAO_PROTEGIDA and posicao > total - ULTIMOS_VERMELHOS:
        return '🟥'
    return '⬜'


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
                              f'{marcador} → {detalhe["pontos"] or 0} pts')
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
