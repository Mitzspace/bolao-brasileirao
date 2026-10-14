"""Mesclagem transacional de uma participação sem palpites em outra existente.

Uso administrativo explícito, após backup. Não mescla contas de login nem
resolve silenciosamente conflitos de pontuação ou de período de participação.
"""
import json
from sqlalchemy import text


def mesclar_sem_palpites(con, origem_id, destino_id, nome):
    if origem_id == destino_id:
        raise ValueError('Selecione registros diferentes.')
    origem = dict(con.execute(text('SELECT * FROM participacao WHERE id=:id'), {'id': origem_id}).mappings().one())
    destino = dict(con.execute(text('SELECT * FROM participacao WHERE id=:id'), {'id': destino_id}).mappings().one())
    if origem['bolao_id'] != destino['bolao_id']:
        raise ValueError('Os registros pertencem a bolões diferentes.')
    for campo in ('status', 'rodada_entrada_id', 'rodada_desistencia_id', 'entrada_legada'):
        if origem[campo] != destino[campo]:
            raise ValueError(f'Conflito de {campo}; revise antes de mesclar.')
    for campo in ('usuario_id', 'participante_legado_id', 'codigo_vinculo', 'email',
                  'motivo_desistencia', 'desistencia_registrada_por', 'desistencia_registrada_em', 'saiu_em'):
        if origem.get(campo) is not None and destino.get(campo) is not None and origem[campo] != destino[campo]:
            raise ValueError(f'Conflito de {campo}; preserve o registro original até revisão.')
    for tabela in ('palpite', 'bonus_rodada'):
        if con.execute(text(f'SELECT count(*) FROM {tabela} WHERE participacao_id=:id'), {'id': origem_id}).scalar():
            raise ValueError('A origem possui palpites ou bônus; exige conciliação individual.')
    valores = dict(destino)
    for campo in ('usuario_id', 'participante_legado_id', 'codigo_vinculo', 'email',
                  'motivo_desistencia', 'desistencia_registrada_por', 'desistencia_registrada_em', 'saiu_em'):
        if campo in valores and valores[campo] is None:
            valores[campo] = origem.get(campo)
    for campo in ('entrou_em', 'pontua_desde'):
        datas = [p[campo] for p in (origem, destino) if p[campo] is not None]
        valores[campo] = min(datas) if datas else None
    valores['papel'] = 'responsavel' if 'responsavel' in (origem['papel'], destino['papel']) else 'participante'
    valores['nome_exibicao'] = nome
    valores['observacao'] = '\n\n'.join(dict.fromkeys(p['observacao'] for p in (destino, origem) if p['observacao'])) or None
    # Só a referência do log muda: o conteúdo, autor e data originais permanecem.
    con.execute(text('UPDATE participacao_log SET participacao_id=:destino WHERE participacao_id=:origem'),
                {'destino': destino_id, 'origem': origem_id})
    # Libera os vínculos únicos antes de transferi-los, na mesma transação.
    con.execute(text('DELETE FROM participacao WHERE id=:id'), {'id': origem_id})
    campos = [c for c in valores if c != 'id']
    con.execute(text('UPDATE participacao SET ' + ', '.join(f'{c}=:{c}' for c in campos) + ' WHERE id=:id'), valores)
    con.execute(text('''INSERT INTO participacao_log
        (participacao_id, alterado_por, alterado_em, acao, valores_anteriores, valores_novos)
        VALUES (:id, NULL, CURRENT_TIMESTAMP, 'mesclagem', :antes, :depois)'''), {
        'id': destino_id,
        'antes': json.dumps({'origem': origem, 'destino': destino}, default=str, ensure_ascii=False),
        'depois': json.dumps(valores, default=str, ensure_ascii=False),
    })
    return valores
