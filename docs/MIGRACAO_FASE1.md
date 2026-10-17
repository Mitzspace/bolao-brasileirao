# Fase 1 — fundação multi-bolão

Branch: `codex/multi-bolao-fase-1`. Migração: `001_multi_bolao`.

## Escopo e compatibilidade

- Um bolão padrão para o Brasileirão 2026, com lançamento por responsável
  habilitado e palpite próprio desabilitado nas configurações.
- 24 participações, preservando os IDs das pessoas e dos 5.652 palpites.
- William (ID 1): admin global, conta ativa e responsável do bolão.
- Ryan (ID 22): conta ativa e responsável do bolão.
- Albert (ID 3): responsável na participação existente, sem conta vinculada.
- Demais pessoas: participação sem login; registros legados e hashes permanecem
  guardados, mas suas contas sintéticas ficam desativadas.
- A tabela `participante` continua sendo a tabela de contas/identidades legadas.
  `Usuario` é um alias do mesmo modelo, sem duplicação de contas ou senhas.
- `participante_legado_id` identifica a origem histórica da participação;
  somente `usuario_id` indica vínculo com conta. Nunca vincular uma conta nova
  pelo nome: a ativação futura usará o convite individual.
- `classico` é a fonte de verdade. O atributo `especial` é um alias, mantendo
  os nomes atuais dos formulários; a coluna histórica `especial` é espelhada.
- `primeiro_marcador` fica no jogo; o campo antigo do resultado é mantido em
  compatibilidade pelos gravadores ORM. O nome `primeiro_gol` do palpite é um
  alias de `jogador_primeiro_gol`, usando a mesma coluna existente.
- Restrições únicas por participação/jogo e por bolão/usuário (múltiplos
  usuários nulos são permitidos), e integridade referencial SQLite ativa.
- 30 créditos históricos de rodada, somando 60 pontos, permanecem separados
  do bônus calculado por jogo. Não atribuir jogos/jogadores retroativamente
  nem substituir créditos sem conciliação individual.

## Pontuação e auditoria

`services/regras_pontuacao.py` é a fonte única dos valores. A função principal
`calcular_pontuacao(palpite, jogo, resultado)` retorna `pontos_placar`,
`pontos_bonus`, `total`, `placar_exato` e `acertou_resultado`.
O adaptador `calcular_pontos` mantém os scripts antigos compatíveis.

O bônus vale em comuns e clássicos, independentemente do placar, inclusive
gol contra pelo nome do jogador. Em 0x0 e com jogador não informado, não há
bônus. Normalização remove acentos, diferenças de caixa e espaços extras.
Pontos não são armazenados no palpite; mudanças oficiais são refletidas na
próxima consulta sem depender de pontuação obsoleta.

Os gravadores ORM atuais criam logs na mesma transação de cada criação ou
alteração, com autor, horário e valores anterior/novo. Rollback desfaz ambos.
Logs são imutáveis e atualizações em lote que ignoram auditoria são recusadas.
Gravação SQL direta não é uma interface de lançamento suportada.

Os registros importados recebem um log `migracao` com o horário verdadeiro
da migração, autor desconhecido e fotografia dos valores. `origem`,
`lancado_por`, `criado_em`, `atualizado_em` e `recebido_em` históricos ficam
nulos. `auditoria_legada` e `entrada_legada` distinguem esses registros;
o início original de participação é desconhecido e não é inventado.
O histórico existente será considerado anterior à migração na futura regra
de elegibilidade; novos participantes terão horário de entrada registrado.

Não se excluem pessoas, palpites ou logs. A rota existente de exclusão de
participante passa a marcar a participação como removida. A mesclagem
automática antiga, que descartava registros duplicados, fica desativada com
mensagem explicativa; isso não altera nomes de rotas ou campos.

## Limites desta fase

As configurações e papéis são a fundação para as próximas fases. A nova
grade, a autorização por bolão em todas as rotas, as telas de convites,
o seletor de bolão e a aplicação completa das configurações nas telas ainda
não estão habilitados. Não anunciar suporte público a múltiplos bolões.

A validação de prazo com `recebido_em` será implementada na Fase 2:
responsáveis só poderão lançar depois do início quando o recebimento for
anterior; correções após o início serão recusadas. Nesta fase os gravadores
administrativos mantêm a política anterior, mas já registram autoria e log.
O fechamento próprio existente é preservado.

A tabela de clássicos sugeridos, confirmação de nomes duvidosos e seletor de
elenco serão tratados nas próximas fases. Não se consulta a API na migração.
Os campos numéricos existentes e o visual Tailwind/base.html são preservados.

Datas novas de auditoria usam UTC; horários antigos de jogos continuam no
formato local de Brasília já existente, sem conversão silenciosa do histórico.
Os scripts antigos de reset/importação destrutiva não devem ser usados.

## Procedimento antes de executar no banco real

O script é `migrations/fase1.py`. Ele suporta somente o SQLite legado
diagnosticado; tabelas inesperadas, responsáveis desconhecidos, conflitos ou
mudança de ranking interrompem a migração. Para outro banco, preparar uma
migração específica, sem reutilizar esta substituição de arquivo.

1. Parar o Flask e qualquer processo de importação/sincronização. Não basta
   apenas fechar o navegador. Manter o app parado até concluir e verificar.
2. Conferir o plano (somente leitura):

   ```powershell
   .venv\Scripts\python.exe -B -m migrations.fase1 plan --database instance/banco.db
   ```

3. Ensaiar em uma cópia, preservando o banco real:

   ```powershell
   .venv\Scripts\python.exe -B -m migrations.fase1 preview --database instance/banco.db
   .venv\Scripts\python.exe -B -m migrations.validar_fase1
   ```

4. Executar a migração autorizada durante a manutenção:

   ```powershell
   .venv\Scripts\python.exe -B -m migrations.fase1 upgrade --database instance/banco.db --app-parado
   ```

Antes da substituição, o script usa a API de backup SQLite e grava
`instance/backups/banco.antes-fase1-<data>-<codigo>.db` e um manifesto `.json`.
Não sobrescreve backups. O novo banco é construído em arquivo separado,
com referências validadas; todos os campos de todos os registros legados e
o ranking de cada pessoa precisam coincidir. A origem é novamente conferida
antes da substituição. Manter os backups privados: contêm dados e hashes.

O processo exige manutenção: a checagem final não substitui a exclusão de
conexões concorrentes. Se houver WAL/journal pendente, o script recusa aplicar.
Mantenha no mesmo local e sistema de arquivos para a substituição do arquivo.

5. Verificar contagens, os 31 clássicos, total agregado de 3.965 pontos,
   ranking individual e acesso de William/Ryan antes de reabrir o app.
   O teste automatizado faz essa comparação usando cópia dos dados reais.
   Não habilitar Albert com uma senha padrão; aguardar conta e vínculo.

O app não executa migração automaticamente: um banco antigo ou incompleto
é recusado com orientação explícita, sem criar tabelas parciais.

## Reversão segura

Com o app parado, usar o manifesto exato impresso pela aplicação:

```powershell
.venv\Scripts\python.exe -B -m migrations.fase1 rollback --database instance/banco.db --manifest "instance/backups/<manifesto-exato>.json" --app-parado
```

O script confere se o backup é o correto e restaura os dados anteriores.
**Se houve lançamento, alteração de resultados, mudança de cache ou qualquer
novo dado após migrar, a reversão é recusada**, para não apagar histórico.
Nesse caso preparar uma migração de correção com os novos dados preservados.
Após reverter o banco, usar também a versão anterior do código. Um banco
revertido é intencionalmente recusado pelo código novo.

O upgrade é idempotente: uma segunda execução na versão aplicada não recria
participações, não duplica logs e não faz outro backup.

## Aplicação local concluída

A migração autorizada foi aplicada no banco `instance/banco.db`, depois de
ensaiar upgrade, reversão e nove telas em uma cópia dos dados reais.

- Backup real: `instance/backups/banco.antes-fase1-20261004T235457-5efe275e.db`.
- Manifesto real: `instance/backups/banco.antes-fase1-20261004T235457-5efe275e.json`.
- Resultado: 1 bolão, 24 participações, 5.652 palpites e 5.652 logs iniciais.
- Os 380 jogos, 31 clássicos, 279 resultados e 60 pontos de créditos históricos
  foram preservados. Ranking individual inalterado; total agregado: 3.965.
- As nove páginas também responderam com HTTP 200 após a migração real.
- A aplicação completa das regras de prazo e configurações aguarda a Fase 2
  e as seguintes; esta migração não libera uso público multi-bolão.
