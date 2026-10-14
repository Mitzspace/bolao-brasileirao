"""Textos de gestão sem dados de conta, usando os pontos já calculados."""


def linha(valor):
    return ' '.join(str(valor or '').split())


def cabecalho(bolao, titulo):
    return [f'*{linha(bolao.nome)} — {titulo}*',
            f'{linha(bolao.campeonato.nome)} · Temporada {bolao.campeonato.ano or "não informada"}', '']


def texto_ranking(bolao, ranking, rodada=None):
    linhas = cabecalho(bolao, f'Ranking · {linha(rodada.nome)}' if rodada else 'Ranking geral')
    for posicao, item in enumerate(ranking, 1):
        bonus = item['bonus_primeiro_gol']
        historico = item['bonus']
        pessoa = item['participante']
        situacao = (f" · desistente ({linha(pessoa.rodada_desistencia.nome)})"
                    if getattr(pessoa, 'status', None) == 'desistente' and pessoa.rodada_desistencia else '')
        linhas.append(f"{posicao}º · {linha(pessoa.nome)}{situacao} · {item['pontos']} pts "
                      f"(bônus 1º gol: {bonus}; créditos históricos: {historico})")
    if not ranking:
        linhas.append('Nenhum participante cadastrado.')
    linhas.extend(['', 'Bônus e créditos já estão incluídos no total.',
                   'Desempate: pontos, placares exatos, acertos de resultado e nome.'])
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
