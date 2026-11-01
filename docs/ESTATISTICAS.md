# Estatísticas: possíveis ganhadores

Aba **Estatísticas**, exclusiva da gestão (`GET /interface/api/estatisticas`, com login de responsável).
Não existe na página pública. A lógica fica em `services/estatisticas.py`.

## Como a chance é estimada

Simulação de Monte Carlo dos jogos que faltam, a partir da classificação atual (`calcular_ranking`):

- Cada jogo simulado sorteia um jogo já encerrado e **todos** repetem o que fizeram nele (cravou, acertou
  o resultado, errou, bônus). Sortear o jogo inteiro mantém o aproveitamento de cada um e a semelhança
  entre os palpites: sortear cada pessoa separadamente exageraria as viradas.
- Os pontos seguem as regras do bolão e o tipo do jogo que falta (clássico ou comum).
- Jogo com `pode_penaltis` sorteia entre os jogos de mata-mata já encerrados e soma os pontos de pênaltis.
  Sem nenhum mata-mata encerrado, sorteia entre todos os jogos e não há pontos de pênaltis a repetir.
- Cortes de eliminação pendentes são aplicados na ordem das rodadas, com a mesma regra de
  `services/eliminacao.py`: quem cai sai da disputa naquela simulação.
- Ganha o 1º pelo mesmo desempate da classificação (pontos, cravadas, resultados, nome).
- A semente depende do bolão e do número de jogos encerrados: a tela não muda ao recarregar.
- O número de simulações se ajusta ao tamanho do bolão (de 1.000 a 5.000) para caber na instância gratuita.

**Limite conhecido:** só entram os jogos cadastrados. Fases de copa ainda não importadas não são simuladas,
e a tela avisa isso nos bolões com mata-mata ou cortes.

## Quem aparece

Só participações `ativo`. Desistentes, removidos e eliminados ficam fora da disputa e mantêm os pontos
na classificação. Quem entrou tarde disputa só as rodadas do seu período; sem histórico, usa o de um colega.

"Sem chance" é só a conta de pontos (o máximo possível não alcança o líder). Os cortes futuros
aparecem na probabilidade, mas não nesse selo.

## Situações (`situacao`)

| Valor | Quando | Na tela |
|---|---|---|
| `simulada` | ativo, com pontos e jogos restantes | probabilidades |
| `sem_resultados` | ninguém pontuou ainda | sem probabilidades, para não eleger um favorito pelo nome |
| `sem_jogos` | todos os jogos cadastrados têm resultado | líder com 100% |
| `encerrado` | bolão finalizado | líder com 100% |
| `desistido` | bolão desistido | só o desempenho |
| `sem_participantes` | nenhum participante ativo | aviso |

A resposta usa `services/cache_publico.py`: qualquer gravação no banco invalida o resultado.
