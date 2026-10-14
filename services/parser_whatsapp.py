"""Parser determinístico: nomes exatos normalizados ou ordem explícita da rodada."""
import re
import unicodedata
from collections import Counter

APELIDOS = {'fla': 'flamengo', 'galo': 'atletico mg', 'timao': 'corinthians',
            'athletico': 'athletico pr', 'atletico mineiro': 'atletico mg',
            'bragantino': 'red bull bragantino'}

CABECALHO = re.compile(r'^\*?\s*rodada\s*[-: ]\s*(\d+)\s*\*?$', re.IGNORECASE)


def rodadas_informadas(texto):
    return {int(m[1]) for linha in texto.splitlines() if (m := CABECALHO.fullmatch(linha.strip()))}


def normalizar(nome):
    nome = ''.join(c for c in unicodedata.normalize('NFKD', nome.casefold()) if not unicodedata.combining(c))
    return ' '.join(p for p in re.findall(r'[a-z0-9]+', nome) if p not in {'fc', 'ec', 'sc'})


def ler_mensagem(texto, jogos, apelidos=None):
    aliases = APELIDOS if apelidos is None else apelidos
    aliases = {normalizar(k): normalizar(v) for k, v in aliases.items()}
    def nome(s):
        n = normalizar(s)
        return aliases.get(n, n)
    linhas, ordem = [], 0
    for original in texto.splitlines():
        if not original.strip():
            continue
        linha = original.strip()
        if CABECALHO.fullmatch(linha):
            ordem = 0
            continue
        linha, estrela, primeiro = linha.partition('★')
        linha = linha.strip()
        numero = re.match(r'^\s*(\d+)\s*(?:\)|\.(?!\d)|-\s+)\s*', linha)
        if re.fullmatch(r'\d+\s*[xX×-]\s*\d+', linha):
            numero = None
        if numero:
            linha = linha[numero.end():]
        achados = list(re.finditer(r'(?<!\d)(\d{1,10})\s*(?:[xX×-]|\ba\b)\s*(\d{1,10})(?!\d)', linha))
        item = {'texto': original, 'jogo_id': None, 'casa': '', 'fora': '',
                'primeiro_gol': primeiro.strip() if estrela else '', 'avisos': []}
        if estrela and not primeiro.strip():
            item['avisos'].append('Marcador ★ sem jogador; primeiro gol ficará sem preenchimento.')
        if len(achados) != 1:
            item['avisos'].append('Não reconhecido: informe um único placar por linha.')
        else:
            placar = achados[0]
            item['casa'], item['fora'] = placar.groups()
            antes, depois = linha[:placar.start()].strip(), linha[placar.end():].strip()
            if not antes and not depois:
                indice = int(numero[1]) - 1 if numero else ordem
                candidatos = [jogos[indice]] if 0 <= indice < len(jogos) else []
                item['avisos'].append('Casamento pela ORDEM dos jogos da rodada; confira os times.')
            else:
                candidatos = [j for j in jogos if nome(j.time_casa) == nome(antes) and nome(j.time_fora) == nome(depois)]
            ordem += 1
            if len(candidatos) == 1:
                item['jogo_id'] = candidatos[0].id
            else:
                item['avisos'].append('Ambíguo: há mais de um jogo compatível.' if candidatos else 'Não reconhecido: times ou posição não correspondem à rodada.')
        linhas.append(item)
    repetidos = Counter(i['jogo_id'] for i in linhas if i['jogo_id'] is not None)
    for item in linhas:
        if repetidos[item['jogo_id']] > 1:
            item['avisos'].append('Jogo repetido: escolha qual linha utilizar.')
    return linhas
