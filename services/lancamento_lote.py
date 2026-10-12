"""Validação integral do formulário antes de qualquer alteração de palpite."""
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def validar_lote(form, jogos, existentes):
    erros, itens = {}, []
    recebido = None
    texto = form.get('recebido_em', '').strip()
    if texto:
        try:
            local = datetime.strptime(texto, '%Y-%m-%dT%H:%M').replace(tzinfo=ZoneInfo('America/Sao_Paulo'))
            recebido = local.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError:
            erros['recebido_em'] = 'Informe uma data e hora válidas (horário de São Paulo).'
    em_massa = form.get('nao_enviou_rodada') == '1'
    for jogo in jogos:
        campos = [f'casa_{jogo.id}', f'fora_{jogo.id}', f'primeiro_{jogo.id}']
        casa, fora, primeiro = [form.get(c, '').strip() for c in campos]
        anterior = existentes.get(jogo.id)
        if anterior and anterior.excluido_por_desistencia:
            if any(c in form for c in campos):
                erros[jogo.id] = 'Palpite guardado após desistência. Confirme a restauração no histórico.'
            continue
        campo_situacao = f'situacao_{jogo.id}'
        situacao = 'nao_enviado' if em_massa else form.get(campo_situacao, anterior.situacao if anterior else 'valido')
        if situacao not in {'valido', 'nao_enviado', 'fora_prazo'} or len(form.getlist(campo_situacao)) > 1:
            erros[jogo.id] = 'Selecione uma situação válida.'
            continue
        if situacao != 'valido':
            # Mantém um placar anterior apenas como histórico; nunca pontua.
            itens.append((jogo, anterior.gols_casa if anterior else 0,
                          anterior.gols_fora if anterior else 0,
                          anterior.primeiro_gol if anterior else None))
            continue
        if anterior and anterior.situacao != 'valido' and not casa and not fora:
            erros[jogo.id] = 'Preencha o placar para tornar o palpite válido.'
            continue
        if any(len(form.getlist(c)) > 1 for c in campos):
            erros[jogo.id] = 'Campos repetidos. Revise este jogo.'
        elif not casa and not fora and not primeiro:
            # Campo vazio nunca exclui um palpite já registrado.
            continue
        elif not casa or not fora:
            erros[jogo.id] = 'Preencha os dois placares deste jogo.'
        elif not all(re.fullmatch(r'[0-9]{1,10}', v) and int(v) <= 2147483647 for v in (casa, fora)):
            erros[jogo.id] = 'Use gols inteiros, de 0 a 2147483647.'
        elif len(primeiro) > 100:
            erros[jogo.id] = 'O nome do jogador deve ter até 100 caracteres.'
        else:
            # Formulários legados que não enviam o bônus não o apagam.
            bonus = (primeiro or None) if campos[2] in form else (anterior.primeiro_gol if anterior else None)
            itens.append((jogo, int(casa), int(fora), bonus if jogo.especial else None))
    if len(form.getlist('recebido_em')) > 1:
        erros['recebido_em'] = 'Informe apenas uma data de recebimento.'
    return itens, recebido, erros
