# Bônus por rodada e atalho para a rodada no desempenho

No painel de desempenho do participante (gestão: Participantes, Classificação, Estatísticas;
link público: detalhe do participante):

- **Rodadas com bônus**: lista as rodadas em que a pessoa ganhou bônus e quantos pontos.
  Soma o bônus de 1º gol calculado pelos palpites e os créditos históricos da planilha
  (`BonusRodada`), que já estão incluídos nos pontos da rodada.
- **Gráfico**: rodadas com bônus têm o ponto dourado; o detalhe da rodada mostra o bônus.
- **Histórico por rodada**: cada rodada mostra "+N de bônus" quando houver.
- **Abrir a rodada**: tocar numa rodada (histórico, lista de bônus ou "Ver palpites da rodada"
  no gráfico) abre:
  - na gestão, **Lançar palpites** daquela rodada e daquela pessoa (só quando o painel é do
    bolão selecionado);
  - no link público, a aba **Palpites** naquela rodada, já filtrada pelo nome da pessoa.

A API passa a enviar `bonus` em cada item de `evolucao` (`/interface/api/participantes/<id>`,
`/interface/api/boloes/<id>/participantes/<pid>/desempenho` e o detalhe público).
