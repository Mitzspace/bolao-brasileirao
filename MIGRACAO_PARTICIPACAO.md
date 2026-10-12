# Etapa 1 — participação por rodada e desistência

Branch: `codex/participantes-lancamento-rapido`. Versão: `002_participacao_desistencia`.

## Decisões aprovadas

- A rodada de desistência é a **primeira rodada em que não participa**.
- Entrada tardia: rodadas anteriores ficam **fora da conta**. A política do bolão
  aceita `fora_da_conta` ou `zero`; o padrão aprovado é `fora_da_conta`.
- Administradores podem lançar e corrigir palpites após o início, sem bloqueio
  por horário. O atraso deve constar no log. Essa decisão substitui a política
  restritiva antes descrita em `MIGRACAO_FASE1.md`. O refinamento desse registro
  e do formulário será feito na Etapa 4. Não exigir recebimento anterior ao início.
- Faixas BSA confirmadas: 1–4 Libertadores, 5–6 pré-Libertadores,
  7–12 Sul-Americana e 17–20 rebaixamento. Alterações visuais ficam na Etapa 7.

## Modelagem desta etapa

- `Participacao`: novo status `desistente`, mantendo `ativo`, `saiu` e `removido`;
  `rodada_entrada_id`, `rodada_desistencia_id` (FK Rodada), `motivo_desistencia`,
  `desistencia_registrada_em` (UTC), `desistencia_registrada_por` (FK conta), `observacao`.
- `ParticipacaoLog`: participação, autor, data UTC, ação e valores anteriores/novos.
  Novas participações e alterações ORM são auditadas na mesma transação.
  Não atribuir autoria a mudanças históricas desconhecidas; os logs começam agora.
  Atribuições por FK ou relacionamento validam o campeonato da rodada no servidor.
- `Palpite.excluido_por_desistencia`: falso inicialmente; muda com auditoria.
  Reativar uma pessoa não limpa automaticamente essa marca. A confirmação para
  restaurar palpites será implementada na Etapa 3.
- `Bolao.politica_entrada_tardia`: fonte explícita da política nova.
  `pontua_desde_entrada` e datas antigas permanecem intactos por compatibilidade;
  a nova elegibilidade usa rodada, sem converter silenciosamente datas antigas.
- `services/elegibilidade.py`: regra única por rodada. Ainda não conectada às
  telas, pendências e rankings nesta etapa; integração na Etapa 3.

Participantes legados continuam com os mesmos status e dados; rodada de entrada
nula preserva seu histórico. Nenhuma desistência é registrada pela migração.
Não há mudança da fórmula, de endpoints nem de nomes de campos de formulário.
Preferências de última rodada ficam para a Etapa 5.

## Migração e preservação

`migrations/participacao.py` não inicializa Flask. Faz backup SQLite exclusivo,
compara schema e dados, adquire transação `BEGIN EXCLUSIVE`, verifica novamente
que a origem não mudou e aplica DDL/dados atomicamente. Uma falha desfaz a transação.
Confere integridade referencial, todos os campos anteriores, IDs, contagens,
rankings individuais gerais e por rodada, cravadas, acertos e créditos históricos.
O manifesto guarda hashes de schema e dados. Não contém tokens.

A migração 001 agora usa o schema congelado `migrations/sql/001_multi_bolao.sql`:
alterações futuras dos modelos não podem criar colunas novas sob um número antigo
de migração. Bancos legados percorrem 001 e depois 002.

Comandos na raiz do projeto:

```powershell
.venv\Scripts\python.exe -B -m migrations.participacao plan
.venv\Scripts\python.exe -B -m migrations.participacao preview
```

`preview` cria uma cópia em `instance/validacao_participacao`, migra, reverte,
confere o estado original e reaplica. Não altera o banco real.

Para aplicar, parar o Flask e importadores/gravadores, executar e reiniciar o app:

```powershell
.venv\Scripts\python.exe -B -m migrations.participacao upgrade --app-parado
```

O backup e o manifesto ficam em `instance/backups/banco.antes-participacao-<data>-<id>`.
Backups nunca são sobrescritos e permanecem ignorados pelo Git. O app recusa abrir
o schema antigo, orientando a migração explícita; não migra automaticamente.

## Reversão

Com app e gravadores parados:

```powershell
.venv\Scripts\python.exe -B -m migrations.participacao rollback --app-parado --manifest "instance/backups/<manifesto-exato>.json"
```

O rollback valida banco, versão e integridade do backup. Só restaura se **nenhum
dado ou schema tiver mudado** desde o upgrade, incluindo cache e logs. Caso contrário,
recusa para preservar os dados novos; preparar migração corretiva nesse caso.
A restauração de schema/dados também é transacional e validada antes do commit.
Para voltar ao código antigo, preservar antes todos os arquivos locais anteriores:
esta branch herdou alterações ainda não commitadas; não usar `git reset --hard`.

## Validação

- Ensaio no banco atual: 24 participações ativas, 5.652 palpites, 5.652 logs de
  palpites, 30 créditos históricos; 3.965 pontos agregados preservados.
- Nove telas responderam HTTP 200 usando a cópia migrada, sem alterar seus dados.
  A tabela oficial usou a resposta já armazenada, sem atualizar o cache via API.
- Testes de migração: backup, upgrade/rollback, idempotência, constraints,
  falha intermediária, concorrência, dados novos, manifesto/backup incompatível
  e encadeamento das migrações 001 → 002.
- Testes de modelos: auditoria com autor, valores antigos/novos, rollback de
  transação, logs imutáveis, rodada de outro campeonato e marca de exclusão persistente.
- Testes da regra central: limites de entrada, desistência, correção e reativação.
  Os testes de efeitos nas telas e confirmação de palpites pertencem à Etapa 3.

## Aplicação local concluída — 11/10/2026

- Backup: `instance/backups/banco.antes-participacao-20261011T225033-3ea8f856.db`.
- Manifesto: `instance/backups/banco.antes-participacao-20261011T225033-3ea8f856.json`.
- Migração real aplicada e integridade/preservação verificadas novamente após o commit.
- As 24 participações continuam ativas; 5.652 palpites, 5.652 logs e 30 créditos
  históricos mantidos. Ranking geral e por rodada inalterados; total: 3.965 pontos.
- Nenhum log de participação histórico foi inventado. A tabela começa vazia.
- Servidor reiniciado na porta 5000; login e início verificados com HTTP 200.
- Suíte completa: 223 testes aprovados. Após congelar o schema da 001, os 14 testes
  de migração passaram, incluindo o novo caso de encadeamento 001 → 002.
  São 224 casos distintos aprovados no total; avisos existentes de APIs legadas.
- A Etapa 2 depende de nova confirmação do usuário. As telas de desistência e
  a aplicação da elegibilidade aos rankings ainda não foram habilitadas.
