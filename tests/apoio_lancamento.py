"""Ajuda dos testes de lançamento: envia um lote no formato antigo (casa_X, fora_X...) pela API."""
import re

URL = '/interface/api/palpites'


def corpo_api(dados):
    corpo = {'participacaoId': int(dados['participante_id']), 'rodadaId': int(dados['rodada_id']),
             'acao': dados.get('acao', 'ficar'), 'jogos': {}}
    if dados.get('recebido_em') is not None:
        corpo['recebidoEm'] = dados['recebido_em']
    if dados.get('nao_enviou_rodada'):
        corpo['naoEnviouRodada'] = True
    for chave, valor in dados.items():
        m = re.fullmatch(r'(casa|fora|primeiro|situacao)_(\d+)', chave)
        if m:
            campo = {'casa': 'casa', 'fora': 'fora', 'primeiro': 'primeiroGol', 'situacao': 'situacao'}[m[1]]
            corpo['jogos'].setdefault(m[2], {})[campo] = str(valor)
    return corpo


def enviar(client, dados):
    return client.post(URL, json=corpo_api(dados))


def texto_erros(resposta):
    dados = resposta.get_json()
    return ' '.join([dados.get('erro', ''), *map(str, (dados.get('erros') or {}).values())])
