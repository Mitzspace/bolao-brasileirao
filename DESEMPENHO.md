# Desempenho e feedback visual (Render Free + Neon)

## O que mudou

### Backend (mesmos resultados, menos trabalho)
| Mudança | Arquivos | Efeito |
|---|---|---|
| Rodadas carregadas com jogos e resultados em lote | `services/contexto_bolao.py` | Jogos, Lançar palpites, Rodadas: **~430 → 10–16 consultas** por tela |
| "Pode excluir rodada" calculado em lote | `services/gestao_campeonato.py`, `routes/api_campeonatos.py` | Campeonato: **462 → 9 consultas** |
| Classificação sem dados repetidos por palpite, regras do bolão resolvidas uma vez, pontuação reaproveitada entre o ranking atual e o da rodada anterior | `services/ranking.py`, `services/evolucao_ranking.py`, `services/gestao_participantes.py` | Dashboard, Participantes, Classificação: **~50% menos processamento** |
| Compressão gzip (JSON, JS, CSS) | `services/http_desempenho.py`, `app.py` | JS da interface ~350 KB → ~95 KB; JSON ~5× menor |
| Arquivos da interface guardados no navegador por 1 ano (o nome muda a cada build); escudos por 7 dias | `services/http_desempenho.py` | Depois do primeiro acesso, a interface abre sem baixar JS/CSS de novo |
| Ordem fixa dos jogos | `models.py`, `services/importador_planilha.py`, `services/grade_palpites.py` | Ver abaixo |
| Dois salvamentos simultâneos de palpites | `routes/api_palpites.py` | O segundo recebe 409 ("acabaram de ser gravados") em vez de erro 500 |
| Índices | `migrations/sql/008_ordem_jogo_indices.sql` | Mantém as consultas rápidas quando os dados crescerem |

Todas as respostas da API foram comparadas antes/depois com o banco real: **idênticas**,
exceto a ordem dos jogos (correção intencional).

### Ordem dos jogos
Antes, a tela de lançamento e a grade mostravam os jogos na ordem física do banco, que
no PostgreSQL muda conforme os registros são atualizados (no Neon já estava embaralhada).
Agora:
- **Rodadas importadas da planilha** (1ª a 30ª, as que já têm palpites): ordem da planilha.
- **Rodadas vindas da API** (31ª em diante e as próximas): ordem de data e horário; jogos sem horário por último.
- Uma nova importação de planilha grava a posição de cada jogo na aba (coluna `jogo.ordem`).

### Frontend
- **Barra de progresso** no topo em toda requisição (troca de aba, salvar, excluir...).
  Se passar de 6 s, aparece o aviso "o servidor gratuito pode estar acordando".
- **Cache no navegador**: voltar a uma aba já aberta mostra os dados na hora e atualiza em
  segundo plano. Qualquer gravação limpa o cache (nenhuma tela mostra dado antigo depois de salvar).
- **Lançar palpites**: ao trocar de pessoa/rodada, o formulário fica bloqueado com
  "Carregando palpites de Fulano…" até os dados certos chegarem; antes, dava para digitar
  e salvar no formulário da pessoa anterior. Botões mostram "Salvando…" e ficam travados;
  o Enter não dispara um segundo salvamento.
- **Clique duplo** em qualquer botão de gravar do sistema vira uma única requisição.
- **Tempo limite** de 75 s (o Render pode levar ~1 min para acordar) com mensagens claras
  de "sem conexão" e "demorou demais" — nas gravações, avisa para conferir antes de repetir.

## Como publicar (ordem importa)
1. **Backup do Neon**: no console do Neon, crie um branch ou snapshot do banco.
2. **SQL no Neon** (SQL Editor): rode `migrations/sql/008_ordem_jogo_indices.sql`.
   Ele só adiciona a coluna `jogo.ordem` e índices; o código atual continua funcionando.
   Confira com a consulta do fim do arquivo: **30 rodadas com ordem e 8 sem**.
3. **Banco local** (se usar): `python -m migrations.ordem_jogo instance/banco.db` (faz backup).
4. **Deploy manual** no Render (o deploy automático está desligado).

Se o código novo for publicado antes do passo 2, o app não sobe e avisa que o schema está
incompleto — nada é alterado no banco.

## Como medir antes e depois
- **Consultas por tela (local)**: `python -m scripts.medir_desempenho instance/banco.db`
  (rode no código antigo e no novo; usa uma cópia do banco).
- **No navegador** (F12 › Rede/Network, com "Desativar cache" desmarcado):
  - coluna *Tempo* das chamadas `/interface/api/...` ao trocar de aba;
  - em `main-*.js`: *Transferido* ~95 KB e `Content-Encoding: gzip`; no segundo acesso, "(cache de disco)".
- **Logs do Render**: cada linha de acesso termina com o tempo da requisição em segundos.

| Tela | Antes | Depois (esperado no Render) |
|---|---|---|
| Jogos / Lançar palpites / Rodadas / Campeonato | ~430–460 consultas (≈2–3 s com o Neon) | 9–16 consultas (≈0,2–0,5 s) |
| Trocar de pessoa no lançamento | ~420 consultas | ~13 consultas |
| Dashboard / Participantes / Classificação | processamento pesado | ~metade do processamento |
| Voltar para uma aba já aberta | recarrega tudo | aparece na hora (atualiza em segundo plano) |
| Primeiro acesso (JS/CSS) | ~400 KB | ~105 KB; depois, 0 KB (cache) |
| Servidor "dormindo" (15 min sem acesso) | 30–60 s sem aviso | igual, com aviso; evitável com o keep-alive abaixo |

## Manter o servidor acordado (opcional, grátis)
O Render Free dorme após **15 min** sem acesso e leva **~1 min** para acordar. Um ping
externo evita isso. Use o endereço `/healthz`: ele **não acessa o banco**, então o Neon
continua suspendendo quando ninguém usa (o Neon Free tem 100 CU-horas/mês por projeto).

**cron-job.org** (gratuito):
1. Crie a conta e clique em *Create cronjob*.
2. URL: `https://SEU-APP.onrender.com/healthz`
3. Agendamento: *Every 10 minutes*, e em *Advanced* restrinja às horas **8 a 23**
   (fuso America/Sao_Paulo).
4. Salve e confira no histórico que as chamadas retornam 200.

Consumo: ~16 h/dia × 31 dias ≈ 500 das **750 horas/mês** gratuitas do Render (as horas
são da conta inteira: outro serviço gratuito na mesma conta divide essa cota).
Fora desse horário, o primeiro acesso volta a levar ~1 min.
