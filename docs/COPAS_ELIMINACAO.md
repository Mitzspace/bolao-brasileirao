# Copas (Libertadores / Sul-Americana / Copa do Brasil / Mineiro) e eliminação de participantes

## Provedores de jogos e resultados

Cada `Campeonato` tem `fonte_api`:

| fonte_api | Provedor | `codigo_api` | Chave no servidor | `Jogo.external_fonte` |
|---|---|---|---|---|
| `football-data` (padrão) | football-data.org v4 | código (`BSA`, `CL`...) | `FOOTBALL_DATA_TOKEN` | `football-data.org` |
| `espn` | ESPN (API pública, **não oficial**) | slug (`conmebol.libertadores`…) | nenhuma | `espn` |
| `api-football` | API-Football (api-sports.io v3) | id da liga (`13`, `11`, `73`, `629`) | `API_FOOTBALL_KEY` | `api-football` |

- Adaptador ESPN: `services/importador_espn.py`. Uma requisição traz a temporada
  (`GET https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates=2025&limit=1000&lang=pt&region=br`).
  A fase (`season.slug`) é traduzida para o vocabulário de `league.round` da API-Football, reusando
  `fase_api_football` / `nomes_rodadas_api_football` / `FORMATO_API_FOOTBALL`. Placar =
  `competitors[].score`; pênaltis = `shootoutScore` quando o status é pós-pênaltis.
- Adaptador API-Football: `services/importador_api_football.py`. Uma requisição traz a temporada
  (`GET https://v3.football.api-sports.io/fixtures?league=13&season=2024&timezone=America/Sao_Paulo`,
  header `x-apisports-key`). Produz os mesmos dicts do importador da football-data
  (`external_id`, `matchday`, `estagio`, `time_casa`, `time_fora`, `data` em Brasília sem tzinfo,
  `status`, `finalizado`, `gols_*_real`) mais `penaltis_*_real`, `pode_penaltis`, `fase` e `status_api`.
- **Placar do bolão = jogo normal = tempo normal + prorrogação.** ESPN/API-Football: placar do jogo
  sem a disputa de pênaltis; pênaltis em campo separado. football-data.org: o `fullTime` de jogo
  decidido nos pênaltis **inclui** a disputa
  ([overtime](https://docs.football-data.org/general/v4/overtime.html)); quando `score.duration` não é
  `REGULAR` usamos `regularTime + extraTime` (sem `regularTime`: `fullTime - penalties`), e
  `score.penalties` vai para `Resultado.penaltis_*_real`.
- **finalizado** (API-Football) só com `FT`, `AET` e `PEN`. Jogo ao vivo nunca é finalizado nem grava
  placar. `AWD`/`WO` **não** são finalizados automaticamente. Na ESPN, só `status.type.completed` com
  `state=post`. Na football-data, jogo em andamento (`IN_PLAY`, `PAUSED`...) também não.
- Erros: a API-Football responde HTTP 200 com `errors` preenchido; isso vira `ErroApiFootball`
  (HTTP 502 na sync manual). ESPN/football-data: erros HTTP com a mensagem do provedor. A chave nunca
  entra na mensagem.
- **Plano gratuito da API-Football**: 100 requisições/dia e restrições de temporadas (confirme o ano na conta). O worker consulta
  cada (liga, ano) no máximo a cada `API_FOOTBALL_INTERVALO_SEGUNDOS` (padrão 3600). A ESPN não exige
  chave; o worker sincroniza campeonatos `espn` sem token. Horários sob demanda (`services/horarios.py`)
  usam football-data ou ESPN; não consultam a API-Football.

## Criação de bolão com modelo de competição

Ao criar um bolão, o responsável escolhe um modelo (`services/competicoes.py: MODELOS_COMPETICAO`):

| Modelo | Fonte | Código | Eliminação |
|---|---|---|---|
| Brasileirão | football-data | `BSA` | não |
| Libertadores | espn | `conmebol.libertadores` | sim |
| Sul-Americana | espn | `conmebol.sudamericana` | sim |
| Copa do Brasil | espn | `bra.copa_do_brazil` | sim |
| Campeonato Mineiro | espn | `bra.camp.mineiro` | sim |
| Copa do Mundo | espn | `fifa.world` | sim |

ou Outro campeonato (nome, fonte e código manuais). O modelo preenche nome, código e fonte (campos
informados prevalecem). Códigos numéricos ainda podem usar `api-football` (com aviso de plano pago);
códigos `CLI`/`CS` na football-data mantêm o aviso do plano pago de lá. Sem fonte informada: slug com
ponto → ESPN, id numérico → API-Football, demais → football-data. A fonte pode ser trocada em
Configurações › Campeonatos › Editar.

`campeonato.codigo_api` aceita até 40 caracteres (slugs ESPN). Migração:
PostgreSQL: `migrations/sql/012_codigo_api_espn.sql`. SQLite já aceita textos maiores mesmo quando
a declaração é VARCHAR(20); `python -m migrations.codigo_api_espn instance/banco.db` apenas confere
as colunas, sem reconstruir tabelas nem alterar dados.

### Fase inicial da importação

O bolão pode começar numa fase (`fase_inicial`: `LAST_32`, `LAST_16`, `QUARTER_FINALS`,
`SEMI_FINALS`, `FINAL`); fases anteriores não são importadas, nem pelo worker. A Copa do Brasil
vem marcada com **oitavas de final** (`LAST_16`). Na Copa do Brasil a ESPN não tem estágio de
16 avos: a fase numerada com 32 times é tratada como 16 avos (`services/competicoes.py:
ordenador_fases`), pois o número dela muda com o regulamento (3ª fase até 2025, 5ª fase em 2026).

### Escudos de times de copas e estaduais

`config_escudos.py: ESCUDOS_COPAS` aponta 163 times da Libertadores, Sul-Americana, Copa do Brasil
e Mineiro (2025-2026) para logos da ESPN salvos em `static/escudos/` (160 px), com as siglas da
ESPN em `SIGLAS_COPAS`. Os escudos da Série A prevalecem. `guarani` fica de fora (Guarani e
Guaraní têm o mesmo nome normalizado). Times sem escudo local usam o `crest` da tabela, quando
houver, ou as iniciais.

## Rodadas de copa

O número inicial do nome define a ordem (`services/contexto_bolao.py: ordem_rodada`), por isso cada
fase tem número fixo pelo formato da competição, nunca só pelos jogos da resposta atual: um import
parcial (por data/rodada) não põe o mata-mata antes dos grupos, e uma fase sorteada depois não
renumera nem duplica as já salvas. Fase já salva com o mesmo rótulo (texto depois de ` · `) é
sempre reaproveitada, mesmo com outro número.

**football-data**: grupos em `Rodada 1..6`, mata-mata `Rodada 7 · Oitavas de final`...
(`FORMATO_COPAS` para CLI/CS; outras numeram após as rodadas de grupo já salvas); preliminares em
`Rodada 0 · Fase preliminar`.

**ESPN e API-Football** (`nomes_rodadas_api_football`, formatos em `FORMATO_API_FOOTBALL`; na ESPN o
slug é mapeado para o id da liga correspondente). Ordem dos blocos: fase preliminar, fases numeradas,
rodadas de grupos/liga, mata-mata.

- Libertadores: `Rodada 1 · 1ª fase` … `Rodada 3 · 3ª fase`, grupos em `4..9`,
  `Rodada 10 · Oitavas de final` … `Rodada 13 · Final`.
- Sul-Americana: `Rodada 1 · 1ª fase`, grupos em `2..7`, `Rodada 8 · Playoffs`,
  `Rodada 9 · Oitavas de final` … `Rodada 12 · Final`.
- Copa do Brasil: `Rodada 1..3 · 1ª..3ª fase`, `Rodada 4 · Oitavas de final` … `Rodada 7 · Final`.
- Campeonato Mineiro: `Rodada 1..8` (primeira fase), `Rodada 9 · Semifinal`, `Rodada 10 · Final`
  (Troféu Inconfidência é ignorado na ESPN).
- Outras ligas: mesmo esquema, com contagens pelo maior valor entre resposta e rodadas salvas.
  Fases desconhecidas vão para o fim com o texto original da API.

As contagens do formato são mínimas: se a API trouxer mais rodadas/fases que o previsto, valem as
maiores. Na sincronização manual, "Número da rodada" é o número local e a busca da ESPN/API-Football
continua sendo uma única requisição da temporada.

**Rodadas de grupos/liga na ESPN:** a ESPN não informa o número da rodada. O adaptador
(`services/importador_espn.py: _inferir_rodadas`) deduz a rodada sobre **todos** os jogos da fase
(antes do filtro de datas): ordena por data, conta o enésimo jogo de cada time e usa o maior
ordinal dos dois times; depois corrige adiamentos (jogo cujos dois times estão repetidos na rodada
r e livres numa mesma rodada s anterior volta para s). Se ainda sobrar time repetido numa rodada
ou rodadas além do número de jogos por time, a fase inteira fica sem número e cai no
agrupamento antigo (`Rodada 4 · Fase de grupos`, `Rodada 1 · Fase de liga`), sem inventar rodadas.
Nome salvo com o mesmo rótulo é reaproveitado; jogos já cadastrados não mudam de rodada
automaticamente. O filtro por rodada usa o número local.

## Tabela de classificação

- football-data: como antes (`services/classificacao.py`).
- ESPN: `services/classificacao_espn.py` consulta
  `https://site.api.espn.com/apis/v2/sports/soccer/{slug}/standings?season=2026&lang=pt&region=br`
  e converte para o formato da football-data, reaproveitando o cache de 15 min em
  `ClassificacaoCache`, o fallback com aviso quando a ESPN falha e os escudos (`crest` da ESPN, com
  id prefixado `espn:`; escudos locais da Série A têm prioridade). Zonas e legendas vêm de
  `note.description/color` da ESPN. Competição sem grupos (Copa do Brasil) mostra mensagem própria.
- API-Football: mensagem de indisponibilidade, sem consultar o provedor errado.

## Pênaltis possíveis (`Jogo.pode_penaltis`)

Calculado na sincronização (`services/competicoes.py: marcar_pode_penaltis`): no mata-mata (inclui
fases preliminares e `Nª fase`) é `True` para o jogo único do confronto na fase ou para o **jogo de
volta** (o posterior dos dois jogos entre o mesmo par na mesma fase); grupos e pontos corridos são
`False`. Num import parcial em que só a ida vem na resposta, a volta já salva na mesma rodada impede
marcar a ida (`services/sync.py: _pode_penaltis`). A sincronização **só liga** a opção: nunca desmarca
um jogo que o responsável marcou à mão.

## Sincronização compartilhada entre bolões

Cada bolão tem seu próprio `Campeonato`. Bolões com a mesma tripla **(fonte_api, codigo_api, ano)**
compartilham uma única chamada à API (`services/sync.py: sync_competicao` /
`campeonatos_da_competicao`), tanto no worker automático quanto na ação "informações" da
sincronização manual. Toda busca de jogo existente considera o `external_fonte` do provedor.
Resultados oficiais (e pênaltis) atualizam todas as cópias do jogo.

**Importação ao criar o bolão:** logo após criar o bolão, `services/criacao_bolao.py:
importar_jogos_iniciais` importa o campeonato completo (uma requisição). Falha de rede ou provedor
pago sem chave não desfaz o bolão: vira aviso na tela. Desligável com
`IMPORTAR_JOGOS_AO_CRIAR=false` (desligado nos testes).

**Fases novas pelo worker (só ESPN):** em campeonatos ESPN, `sync_competicao` também cria os jogos
cujo `external_id` o campeonato ainda não tem (`services/sync.py: importar_jogos_novos`), com a
mesma resposta, sem requisição extra. Jogos já salvos ficam fora para não criar rodadas vazias em
bolões com nomes antigos. Campeonatos ESPN ainda vazios também entram no ciclo. football-data e
API-Football continuam só atualizando horários e resultados.

O worker (`python -m services.sync_automatico`) usa `API_FOOTBALL_KEY` nos campeonatos api-football,
`FOOTBALL_DATA_TOKEN` nos football-data, e nenhuma chave nos ESPN; provedor pago sem chave é pulado
com aviso no log. A sincronização manual usa o provedor do campeonato (token do formulário opcional
exceto na ESPN).

## Eliminação de participantes por fase

Opção do bolão (`bolao.eliminacao_participantes`, desligada por padrão), configurada em
Configurações → Eliminação de participantes. Cada corte (`corte_eliminacao`) diz: após a rodada X,
só os N melhores seguem. O corte só vale quando todos os jogos até a rodada X têm resultado.
Quem é eliminado sai do ranking geral e do ranking das rodadas posteriores ao corte.
Regra em `services/eliminacao.py`.

## Migração (obrigatória antes de publicar)

- SQLite: `python -m migrations.eliminacao instance/banco.db` e
  `python -m migrations.penaltis instance/banco.db` (fazem backup antes; idempotentes).
  `python -m migrations.codigo_api_espn instance/banco.db` só verifica as colunas, sem gravação.
- PostgreSQL (Neon): aplicar `migrations/sql/010_eliminacao.sql`, `011_penaltis.sql` e
  `012_codigo_api_espn.sql` após backup.

O app recusa iniciar enquanto a migração de pênaltis/`fonte_api` não for aplicada; em Postgres também
exige `codigo_api` com pelo menos 40 caracteres.

## Verificação da integração ESPN

Consulta de leitura executada em 18/10/2026, temporada 2026, com o adaptador final:

| Competição | Jogos convertidos | Rodadas locais | Tabela |
|---|---:|---|---|
| Libertadores | 155 | 1–3 fases, grupos 4–9 (16 jogos cada), 10 Oitavas … 13 Final | 8 grupos |
| Sul-Americana | 157 | 1ª fase, grupos 2–7 (16 jogos cada), 8 Playoffs … 12 Final | 8 grupos |
| Copa do Brasil | 155 | 1–5 fases, 6 Oitavas … 9 Final | sem grupos |
| Mineiro | 53 (sem Troféu Inconfidência) | 1–8 (6 jogos cada), 9 Semifinal, 10 Final | 3 grupos |

Importação completa ponta a ponta (bolão criado pelo modelo + `sync_jogos` completo +
`dados_tabela`) executada em 18/10/2026. Na fase de grupos/liga, cada time aparece exatamente uma
vez por rodada. Essas contagens descrevem a resposta recebida, não uma garantia de cobertura futura.
A Copa do Brasil 2026 retornou cinco fases numeradas antes das oitavas; o nomeador ajustou
as oitavas para a rodada local 6 e a final para a rodada local 9.
O serviço é uma interface pública não oficial: disponibilidade e formato podem mudar.

## Copa do Mundo (tema e seleções)

- Modelo `copadomundo` (`fifa.world`, ESPN): 3 rodadas de grupos, 16 avos, oitavas, quartas, semifinal, 3º lugar e final.
- Logo/bandeira e sigla de cada seleção: `config_selecoes.py` (CDN da ESPN; edite lá para trocar). `services/escudos.py` usa esse mapa quando o time não tem escudo local.
- Tema visual: `services/competicoes.tema_do_campeonato` devolve `tema` nos bolões; o frontend aplica `data-tema` na `<html>` (`lib/temaCampeonato.ts`) e as paletas ficam em `index.css`. Para um novo tema: variáveis em `index.css`, entrada em `TEMAS_POR_CODIGO` e em `TEMAS` (frontend).

