# Situação dos palpites e sincronização

O lançamento permite marcar toda a rodada como não enviada ou escolher por jogo: válido, não enviado e fora do prazo. Os dois últimos não pontuam (incluindo bônus), ficam registrados no histórico e contam como lançamento resolvido. Para corrigir, selecione válido e preencha o placar. Lançar administrativamente depois do início não invalida automaticamente um palpite recebido no prazo.

## Banco existente

Antes de iniciar a versão nova, execute:

```powershell
.venv\Scripts\python.exe -m migrations.situacao_palpite instance/banco.db
```

A migração SQLite cria backup ao lado do banco, mantém os registros anteriores como válidos e pode ser executada novamente. Para PostgreSQL, faça backup e execute `ALTER TABLE palpite ADD COLUMN situacao VARCHAR(20) NOT NULL DEFAULT 'valido' CHECK (situacao IN ('valido', 'nao_enviado', 'fora_prazo'));` uma vez.

## Sincronização automática

Configure FOOTBALL_DATA_TOKEN e inicie **uma instância** do worker junto do servidor:

```powershell
.venv\Scripts\python.exe -m services.sync_automatico
```

Em hospedagem com Procfile, habilite o processo `worker` incluído. Use o mesmo DATABASE_URL do servidor. O primeiro ciclo roda ao iniciar; os seguintes a cada 900 segundos, configuráveis por SYNC_INTERVALO_SEGUNDOS (mínimo 60). O processo precisa permanecer ativo; não depende de visitas ao site. Os campeonatos com código API e rodadas cadastradas são atualizados usando seu ano como temporada. Falhas são registradas e repetidas no próximo ciclo. Jogos existentes são associados por ID da API ou rodada e times; não cria jogos novos nem altera palpites. Atualiza horários e resultados finais; o primeiro marcador continua manual.

A tabela BSA exibe Mineiro como Atlético-MG e Paranaense como Atlético Paranaense, inclusive a partir do cache.
