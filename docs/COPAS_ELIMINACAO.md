# Copas (Libertadores / Sul-Americana / Copa do Brasil / Mineiro) e eliminação de participantes

## Provedores de jogos e resultados

Cada `Campeonato` tem `fonte_api`:

| fonte_api | Provedor | `codigo_api` | Chave no servidor | `Jogo.external_fonte` |
|---|---|---|---|---|
| `football-data` (padrão) | football-data.org v4 | código (`BSA`, `CL`...) | `FOOTBALL_DATA_TOKEN` | `football-data.org` |
| `api-football` | API-Football (api-sports.io v3) | id da liga (`13`, `11`, `73`, `629`) | `API_FOOTBALL_KEY` | `api-football` |

- Adaptador: `services/importador_api_football.py`. Uma requisição traz a temporada inteira
  (`GET https://v3.football.api-sports.io/fixtures?league=13&season=2024&timezone=America/Sao_Paulo`,
  header `x-apisports-key`; query montada com `urlencode`). Produz os mesmos dicts do importador
  da football-data (`external_id`, `matchday`, `estagio`, `time_casa`, `time_fora`, `data` em
  Brasília sem tzinfo, `status`, `finalizado`, `gols_*_real`) mais `penaltis_*_real`,
  `pode_penaltis`, `fase` (rótulo em português) e `status_api` (status original da API).
- **Placar do bolão = jogo normal = tempo normal + prorrogação.** API-Football: `goals`; pênaltis em
  `score.penalty`. football-data.org: o `fullTime` de jogo decidido nos pênaltis **inclui** a disputa
  ([overtime](https://docs.football-data.org/general/v4/overtime.html)); quando `score.duration` não é
  `REGULAR` usamos `regularTime + extraTime` (sem `regularTime`: `fullTime - penalties`), e
  `score.penalties` vai para `Resultado.penaltis_*_real`.
- **finalizado** só com `FT`, `AET` e `PEN`. Jogo ao vivo (`1H`, `HT`, `2H`, `ET`, `BT`, `P`, `LIVE`,
  `SUSP`, `INT`) nunca é finalizado nem grava placar, embora a API já mande `goals` parcial.
  `AWD` (vitória administrativa) e `WO` **não** são finalizados automaticamente: o placar é de
  tribunal (ou nem houve jogo) e o responsável lança à mão como achar justo. `PST`, `CANC`, `ABD`,
  `NS` e `TBD` também não. Na football-data, jogo em andamento (`IN_PLAY`, `PAUSED`...) também não.
- Erros: a API-Football responde HTTP 200 com `errors` preenchido (ex.:
  `{"plan": "Free plans do not have access to this season, try from 2022 to 2024."}`); isso vira
  `ErroApiFootball` com mensagem pronta, exibida na sincronização manual (HTTP 502). Erros HTTP da
  football-data mostram o `message` do provedor. A chave nunca entra na mensagem.
- **Plano gratuito da API-Football**: 100 requisições/dia e só temporadas 2022–2024 (a temporada
  atual exige plano pago). Por isso o worker consulta cada (liga, ano) no máximo a cada
  `API_FOOTBALL_INTERVALO_SEGUNDOS` (padrão 3600), e a atualização de horários sob demanda da aba
  Jogos (`services/horarios.py`) não consulta a API-Football (os horários vêm da sincronização).

## Criação de bolão com modelo de competição

Ao criar um bolão, o responsável escolhe um modelo (`services/competicoes.py: MODELOS_COMPETICAO`):

| Modelo | Fonte | Código | Eliminação |
|---|---|---|---|
| Brasileirão | football-data | `BSA` | não |
| Libertadores | api-football | `13` | sim |
| Sul-Americana | api-football | `11` | sim |
| Copa do Brasil | api-football | `73` | sim |
| Campeonato Mineiro | api-football | `629` | sim |

ou Outro campeonato (nome, fonte e código manuais). O modelo preenche nome, código e fonte (campos
informados prevalecem) e marca "Eliminar participantes por fase". Os modelos api-football avisam que
a temporada atual exige plano pago da API-Football; códigos `CLI`/`CS` na football-data mantêm o
aviso do plano pago de lá. `criar_bolao(..., fonte_api=None)` grava a fonte; sem fonte informada ela
é inferida do código (id numérico = api-football), o que coincide com os modelos. A fonte pode ser
trocada depois em Configurações › Campeonatos › Editar.

> Pendente (arquivo de outro fluxo): `routes/api_boloes.py` ainda não repassa o campo `fonte_api`
> que o formulário envia para `criar_bolao`; até lá vale a inferência pelo código.

## Rodadas de copa

O número inicial do nome define a ordem (`services/contexto_bolao.py: ordem_rodada`), por isso cada
fase tem número fixo pelo formato da competição, nunca só pelos jogos da resposta atual: um import
parcial (por data/rodada) não põe o mata-mata antes dos grupos, e uma fase sorteada depois não
renumera nem duplica as já salvas. Fase já salva com o mesmo rótulo (texto depois de ` · `) é
sempre reaproveitada, mesmo com outro número.

**football-data**: grupos em `Rodada 1..6`, mata-mata `Rodada 7 · Oitavas de final`...
(`FORMATO_COPAS` para CLI/CS; outras numeram após as rodadas de grupo já salvas); preliminares em
`Rodada 0 · Fase preliminar`.

**API-Football** (`nomes_rodadas_api_football`, formatos em `FORMATO_API_FOOTBALL`). `league.round`
é normalizado por `fase_api_football` (`1st Round` → `1ª fase`, `Group Stage - 3` → fase de grupos,
`Regular Season - N`, `Knockout Round Play-offs` → Playoffs, `Round of 16`/`8th Finals` → Oitavas,
`Quarter-finals`, `Semi-finals`, `Final`...). Ordem dos blocos: fase preliminar, fases numeradas
(`1st/2nd/3rd Round`), rodadas de grupos/liga, mata-mata.

- Libertadores (13): `Rodada 1 · 1ª fase`, `Rodada 2 · 2ª fase`, `Rodada 3 · 3ª fase`,
  `Rodada 4 · Fase de grupos - 1ª rodada` ... `Rodada 9 · Fase de grupos - 6ª rodada`,
  `Rodada 10 · Oitavas de final`, `Rodada 11 · Quartas de final`, `Rodada 12 · Semifinal`,
  `Rodada 13 · Final`.
- Sul-Americana (11): `Rodada 1 · 1ª fase`, grupos em `2..7`, `Rodada 8 · Playoffs`,
  `Rodada 9 · Oitavas de final` ... `Rodada 12 · Final`.
- Copa do Brasil (73), só mata-mata: `Rodada 1..3 · 1ª..3ª fase`, `Rodada 4 · Oitavas de final` ...
  `Rodada 7 · Final`.
- Campeonato Mineiro (629): `Rodada 1..8` (primeira fase), `Rodada 9 · Semifinal`, `Rodada 10 · Final`.
- Outras ligas: mesmo esquema, com contagens pelo maior valor entre resposta e rodadas salvas
  (pontos corridos sem fase anterior ficam `Rodada N`, como no Brasileirão). Fases desconhecidas
  vão para o fim com o texto original da API.

As contagens do formato são mínimas: se a API trouxer mais rodadas/fases que o previsto, valem as
maiores. Na sincronização manual da API-Football, "Número da rodada" é o número local (ex.: 10 =
Oitavas na Libertadores) e a busca continua sendo uma única requisição da temporada.

## Pênaltis possíveis (`Jogo.pode_penaltis`)

Calculado na sincronização dos dois provedores (`services/competicoes.py: marcar_pode_penaltis`):
no mata-mata (inclui fases preliminares e `Nª fase`) é `True` para o jogo único do confronto na
fase ou para o **jogo de volta** (o posterior dos dois jogos entre o mesmo par na mesma fase);
grupos e pontos corridos são `False`. Num import parcial em que só a ida vem na resposta, a volta
já salva na mesma rodada impede marcar a ida (`services/sync.py: _pode_penaltis`). A sincronização
**só liga** a opção: nunca desmarca um jogo que o responsável marcou à mão.

## Sincronização compartilhada entre bolões

Cada bolão tem seu próprio `Campeonato`. Bolões com a mesma tripla **(fonte_api, codigo_api, ano)**
compartilham uma única chamada à API (`services/sync.py: sync_competicao` /
`campeonatos_da_competicao`), tanto no worker automático quanto na ação "informações" da
sincronização manual. Toda busca de jogo existente considera o `external_fonte` do provedor.
Resultados oficiais (e pênaltis) atualizam todas as cópias do jogo.

O worker (`python -m services.sync_automatico`) usa `API_FOOTBALL_KEY` nos campeonatos api-football
e `FOOTBALL_DATA_TOKEN` nos demais; provedor sem chave é pulado com aviso no log. A sincronização
manual usa o provedor do campeonato e a chave do servidor (o token do formulário é opcional).

## Eliminação de participantes por fase

Opção do bolão (`bolao.eliminacao_participantes`, desligada por padrão), configurada em
Configurações → Eliminação de participantes. Cada corte (`corte_eliminacao`) diz: após a rodada X,
só os N melhores seguem. O corte só vale quando todos os jogos até a rodada X têm resultado.
Quem é eliminado sai do ranking geral e do ranking das rodadas posteriores ao corte.
Regra em `services/eliminacao.py`.

## Migração (obrigatória antes de publicar)

- SQLite: `python -m migrations.eliminacao instance/banco.db` e
  `python -m migrations.penaltis instance/banco.db` (fazem backup antes; idempotentes).
- PostgreSQL (Neon): aplicar `migrations/sql/010_eliminacao.sql` e `migrations/sql/011_penaltis.sql`
  após backup (`011` cria `campeonato.fonte_api`, `jogo.pode_penaltis` e os pênaltis de palpite/resultado).

O app recusa iniciar enquanto a migração não for aplicada.
