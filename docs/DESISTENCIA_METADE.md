# Desistência só até a metade do campeonato

Configuração por bolão (aba **Participantes**, chave "Desistência só até a metade do campeonato").
Começa **desligada** em todos os bolões, ou seja, o comportamento é o mesmo de antes.

## Como funciona

- **Metade do campeonato** é a última rodada da primeira metade, pela ordem das rodadas cadastradas
  (38 rodadas → Rodada 19; com número ímpar arredonda para cima: 19 rodadas → Rodada 10).
- Desistência **até a metade** (rodada de desistência ≤ metade): igual a hoje. A pessoa sai da tabela
  quando os desistentes são ocultados (classificação, link público, texto do WhatsApp).
- Desistência **depois da metade**: a pessoa continua marcada como desistente, deixa de ser cobrada e de pontuar
  a partir da rodada de desistência, mas **continua na tabela** com os pontos que já tinha. Isso vale mesmo com
  "Ocultar desistentes" ligado, e ela conta na posição e nas cores do texto compartilhado.
- Ligar ou desligar a regra não altera palpites nem pontos. Só muda quem aparece na tabela.

A prévia da desistência avisa quando a pessoa vai continuar na tabela.

## Migração (obrigatória antes de publicar)

- SQLite: `python -m migrations.desistencia_metade CAMINHO_DO_BANCO` (faz backup antes; idempotente).
- PostgreSQL (Neon): aplique `migrations/sql/013_desistencia_metade.sql` após backup.

Sem a coluna `bolao.desistencia_ate_metade`, o `create_app` falha com a mensagem apontando esta migração.

# Cores proporcionais no texto da classificação

O texto "Compartilhar classificação" (WhatsApp) colore as posições proporcionalmente ao número de pessoas
na tabela: 20% verde 🟩, 5% amarelo 🟨 (mínimo 1), 25% azul 🟦, os últimos 20% vermelho 🟥 e o restante branco ⬜
(arredondamento para o inteiro mais próximo). Com 20 participantes: 4 verdes, 1 amarelo, 5 azuis, 6 brancos e 4 vermelhos.
Com poucos participantes as faixas do topo têm prioridade sobre o vermelho. A legenda da prévia é gerada para o total atual.
