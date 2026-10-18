"""Conversão dos modelos para o JSON da nova interface (somente leitura)."""
from services.escudos import escudo_time
from services.relogio import agora_brasilia

DIAS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']


def texto_data(data):
    """Datas são horário de Brasília sem fuso no banco; o texto sai pronto do servidor."""
    if data is None:
        return None
    return f"{DIAS[data.weekday()]} {data:%d/%m} · {data:%H:%M}"


def status_jogo(jogo):
    if jogo.resultado is not None:
        return 'encerrado'
    if jogo.encerrado or (jogo.data is not None and agora_brasilia() >= jogo.data):
        return 'aguardando'  # já começou ou foi encerrado sem resultado lançado
    return 'agendado'


def serializar_jogo(jogo, campeonato_id):
    resultado = jogo.resultado
    return {
        'id': jogo.id,
        'casa': jogo.time_casa,
        'fora': jogo.time_fora,
        'escudoCasa': escudo_time(jogo.time_casa, campeonato_id=campeonato_id),
        'escudoFora': escudo_time(jogo.time_fora, campeonato_id=campeonato_id),
        'data': jogo.data.isoformat() if jogo.data else None,
        'dataTexto': texto_data(jogo.data),
        'classico': bool(jogo.classico),
        'status': status_jogo(jogo),
        'golsCasa': resultado.gols_casa_real if resultado else None,
        'golsFora': resultado.gols_fora_real if resultado else None,
        'podePenaltis': bool(jogo.pode_penaltis),
        'penaltisCasa': resultado.penaltis_casa_real if resultado else None,
        'penaltisFora': resultado.penaltis_fora_real if resultado else None,
    }


def serializar_item_ranking(item):
    pessoa = item['participante']
    return {
        'participacaoId': pessoa.id,
        'nome': pessoa.nome,
        'status': getattr(pessoa, 'status', 'ativo'),
        'posicao': item.get('posicao'),
        'variacao': item.get('variacao'),
        'pontos': item['pontos'],
        'pontosPalpites': item['pontos_palpites'],
        'bonus': item['bonus'],
        'bonusPrimeiroGol': item['bonus_primeiro_gol'],
        'cravadas': item['cravadas'],
        'acertosVencedor': item['acertos_vencedor'],
    }


def serializar_regras(bolao):
    from services.regras_pontuacao import regras_do_bolao
    r = regras_do_bolao(bolao)
    return {'comumExato': r['comum_exato'], 'comumResultado': r['comum_resultado'],
            'classicoExato': r['classico_exato'], 'classicoResultado': r['classico_resultado'],
            'primeiroGol': r['primeiro_gol'],
            'penaltisExato': r['penaltis_exato'], 'penaltisVencedor': r['penaltis_vencedor']}
