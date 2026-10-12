# Etapa 2 — Meus bolões

Implementada na branch de trabalho isolada `codex/gestao-admin-etapa1`, mantendo a Etapa 1.

Os cartões em `/boloes` mostram nome, campeonato, temporada, rodada de referência,
participantes ativos e palpites faltantes. O contexto compartilhado existente
(`bolao_atual`, `boloes_disponiveis`, `participacao_atual`, `responsavel_bolao`) e o
menu condicional foram reaproveitados. Os resumos são calculados em lote somente
na tela de seleção, sem acrescentar consultas ao context processor.

No modo de gestão, o login abre a lista quando existem vários bolões, mantendo a
última seleção na sessão. Com um único bolão, a seleção continua automática.
A memória pertence à conta e à sessão do navegador; não há sincronização entre dispositivos.

## Critérios dos indicadores

- Rodadas são ordenadas pelo número no nome e, em caso de empate, nome e ID.
- Prioriza-se a primeira rodada aberta com pelo menos um jogo sem resultado e
  não encerrado. Se nenhuma estiver aberta, usa-se a primeira com jogo pendente.
- Quando todos os jogos estão concluídos, mostra-se a última rodada com jogos,
  identificada como “Última rodada”. Rodadas sem jogos não são escolhidas.
- A tela `/jogos`, quando acessada sem rodada explícita, usa a mesma referência.
- Participantes ativos incluem responsáveis que possuem participação ativa.
- Pendências são pares de participação ativa/jogo sem palpite na rodada escolhida.
  São contadas separadamente por bolão, mesmo com jogos compartilhados.
  Incluem jogos já iniciados ou concluídos e não representam permissão para lançar.
- Sem jogos, o cartão informa isso e apresenta um traço no campo de pendências.

Não foram alterados URLs, endpoints, campos de formulário, esquema ou dados do
banco, pontuação, sincronização ou regras de lançamento.

## Validação

- 161 testes aprovados, incluindo quatro novos casos de contagem, rodada,
  isolamento entre bolões, login com memória e seleção automática.
- Conferência independente, par a par, em cópia do banco atual: 29ª rodada,
  24 participações ativas, 10 jogos e 240 palpites faltantes.
- Renderização das páginas `/boloes` e `/jogos` validada com os dados da cópia.
- SHA-256 do banco original permaneceu igual antes e depois da validação.

A Etapa 3 aguarda confirmação: aperfeiçoar a troca de aba/rodada, revisar as
permissões de todas as rotas, gerir múltiplos responsáveis e adotar as URLs
por bolão já propostas, mantendo compatibilidade com os caminhos antigos.
