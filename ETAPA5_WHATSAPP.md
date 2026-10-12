# Etapa 5 — textos para WhatsApp

Implementada na branch `codex/gestao-admin-etapa1`. Sem migração, alteração de
pontuação ou envio de mensagens. O link público não foi implementado.

## Uso

- Em Ranking, selecione Geral ou uma rodada e clique em Mostrar ranking.
- Copiar ranking copia o texto do período exibido: posição, nome de exibição,
  total de pontos, bônus de primeiro gol e créditos históricos.
- Na grade de palpites da rodada, Copiar resumo da rodada reúne os jogos,
  resultados registrados, primeiro marcador, palpites e pontos por participante,
  além dos totais da rodada.
- Conferir texto ou copiar manualmente abre uma prévia em campo somente leitura.
  Se a área de transferência não estiver disponível ou a permissão for negada,
  o botão abre e seleciona esse texto para cópia manual.
- Atualize a página após corrigir resultados; o texto corresponde ao retrato
  da página carregada. Colar e enviar no WhatsApp são ações do administrador.

## Regras preservadas

- O ranking geral usa os mesmos totais e critérios de desempate existentes.
- O filtro `rodada_id` restringe tanto palpites quanto créditos históricos;
  rodadas de outro campeonato e parâmetros inválidos são recusados.
- O bônus de primeiro gol já está em pontos_palpites; é detalhado no texto,
  sem somá-lo novamente. Créditos históricos continuam na coluna Bônus.
- Participações inativas permanecem nos rankings e históricos, como antes.
- Os textos são exibidos apenas para responsáveis autorizados e não contêm
  e-mails, senhas, códigos de convite ou vínculos de conta.
- Jogos sem resultado aparecem como aguardando resultado; seus palpites são
  omitidos do resumo copiável. Não houve alteração na grade administrativa.
- A troca de bolão no ranking preserva a rodada quando o campeonato é o mesmo.

Não há nova rota de exportação: o texto é renderizado nas páginas já protegidas.
O endpoint ranking foi preservado, com o novo parâmetro opcional `rodada_id`.

## Validação

- 204 testes aprovados, incluindo cinco novos casos sobre textos, totais,
  filtragem, isolamento, escape HTML, autorização e correção de resultados.
- Três cenários JavaScript simulados: cópia bem-sucedida, permissão negada e
  contexto inseguro, com fallback para seleção manual nos dois últimos.
- Conferência dos totais dos 24 participantes, geral e por rodada, e geração
  do resumo em cópia do banco atual. SHA-256 do banco original inalterado.
- Build do CSS Tailwind concluído. Nenhuma chamada à API externa ou envio ao WhatsApp.

O link público somente leitura permanece fora do escopo aprovado e depende
de uma aprovação específica futura.
