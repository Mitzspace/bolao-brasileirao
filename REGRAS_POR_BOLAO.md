# Regras de pontuação por bolão

Cada bolão tem suas próprias regras (Bolões › Ver classificação › Regras):
placar exato e resultado em jogo comum, placar exato e resultado em clássico e bônus
de primeiro gol. Valores de 0 a 99; o placar exato precisa valer pelo menos o mesmo
que acertar só o resultado.

A mudança é **retroativa**: a pontuação é sempre calculada na hora a partir dos
palpites e resultados, então todas as rodadas (inclusive as já jogadas), a classificação,
a grade e o gráfico passam a usar os novos valores. Nenhum palpite é alterado e
voltar aos valores antigos devolve exatamente a pontuação anterior.
Créditos históricos importados (BonusRodada) não mudam: são valores fixos.

## Migração (antes de publicar o código)

1. Local: `python -m migrations.regras_bolao instance/banco.db` (faz backup).
2. Neon: rode `migrations/sql/007_regras_bolao.sql` no SQL Editor.

Os bolões existentes recebem os valores atuais (comum 3/1, clássico 5/3, primeiro gol +2).
