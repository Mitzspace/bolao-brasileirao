# Publicar gratuitamente: Render Free + Neon Free

Guia atualizado em 12/10/2026. A preparação não publica o sistema, não cria contas,
não contrata serviços e não envia os dados existentes. A implantação anterior
com disco e Redis pagos foi substituída.

## 1. O que muda e quais são os limites

A aplicação continua Flask/Jinja com SQLAlchemy, Flask-Login, CSRF, openpyxl,
Tailwind/Alpine e API football-data.org. Em produção, o banco passa a ser
PostgreSQL no Neon; SQLite continua no desenvolvimento. Dados, hashes de senha,
IDs, vínculos e auditoria são preservados na migração. Login, administração,
lançamento de palpites, resultados, ranking, importações e gestão de participantes
permanecem disponíveis.

| Item | Consequência no plano gratuito |
| --- | --- |
| Render suspende após 15 minutos sem tráfego | Primeira visita após inatividade pode levar cerca de um minuto. Não há disponibilidade imediata garantida 24h. |
| Arquivos do Render são temporários | Nenhum SQLite de produção ou backup ficará no container. Upload XLSX é processado e seus registros vão para Neon; o arquivo original não é arquivo permanente. |
| Render Free não tem Shell/SSH nem jobs avulsos | Inicialização, migração, criação do administrador e backups serão feitos pelo seu computador conectado ao Neon. Depois disso o site funciona sem esse computador ligado. |
| Sincronização periódica | Não roda enquanto o Render estiver suspenso. A sincronização manual pelo administrador é a opção recomendada. O worker existente permanece opcional, mas sem garantia de periodicidade. |
| Limites de requisições em memória | Login continua limitado. Os contadores são perdidos no reinício. Apenas um worker/instância; threads compartilham os contadores. |
| Quotas gratuitas | Atingir limites pode suspender aplicação/banco ou impedir novas gravações/builds. Não ativar upgrade para contornar isso. |
| Email de recuperação | Continua sem envio automático; mantenha contato com o administrador. Nenhum email pago foi adicionado. |

Redis era usado somente pelo Flask-Limiter, não por sessões, filas, jogos ou
usuários. Foi retirado das dependências e do Blueprint. O limiter permanece
habilitado, inclusive a proteção de login (10/h), com aceite explícito do modo
de processo único. Não configure vários workers nem GUNICORN_CMD_ARGS que
sobrescreva workers. Não publique uma segunda instância apontando ao mesmo
banco sem rever os limites.

As sondas do Render usam /healthz, que verifica apenas se a aplicação está viva.
A rota /readyz faz uma consulta de banco e retorna 503 em falha, sem detalhes
sensíveis. Use /readyz pontualmente; monitoramento frequente manteria o Neon
ativo e gastaria sua quota. /healthz 200 não comprova conexão com o banco.

Fontes oficiais:
[limitações Render Free](https://render.com/docs/free),
[tráfego e cobrança Render](https://render.com/docs/outbound-bandwidth),
[Neon Free: 1 GB por projeto, anunciado em 02/10/2026](https://neon.com/blog/neon-free-plan-1-gb-per-project),
[uso da quota Neon](https://neon.com/blog/how-to-make-the-most-of-neons-free-plan).
Confira os limites efetivos no painel: planos podem mudar. O Neon Free oferece
100 CU-h/mês por projeto na documentação consultada. O armazenamento é separado
do compute: suspender o compute não apaga os registros. Isso não é garantia de
armazenamento eterno nem substitui backup.

## 2. Como manter custo zero

- Crie contas **Free** no Neon e Render. No Render, workspace Hobby e web service
  com instância **Free** são configurações distintas; confira ambas.
- Não cadastre cartão/formas de pagamento, não aceite trials de planos pagos e
  não habilite upgrades. Se a criação exigir pagamento, pare: não autorize a
  contratação. No Render sem forma de pagamento, excedentes suspendem serviços
  ou builds, em vez de serem cobrados, conforme a documentação acima.
- Não crie Render PostgreSQL Free: ele expira em 30 dias. Use **Neon Free**.
- Não crie Key Value/Redis, Persistent Disk, cron ou background worker separado.
- Use o subdomínio onrender.com. Não é necessário comprar domínio.
- Não use robôs/pings para evitar a suspensão: consomem quota e não resolvem as
  limitações do plano. Observe avisos e uso nos painéis.
- O GitHub Actions fornecido é **manual**, não dispara a cada push. Pode ser
  ignorado. Se executá-lo em repositório privado, use somente minutos incluídos,
  sem orçamento pago nem forma de pagamento. Os testes locais não cobram nada.

Nenhuma configuração de código pode garantir a política comercial futura do
provedor. A implantação preparada só pede uma web Free; não inclui recurso pago.

## 3. Preparar contas e repositório

1. Crie/acesse GitHub, Neon e Render. A conta football-data.org é opcional para
   sincronização/classificação; escolha apenas o acesso gratuito disponível.
2. Envie a pasta **bolao2** para um repositório privado. Ela é o sistema Flask;
   palpita-liga-main é outro projeto e não é dependência deste deploy.
3. Revise git status e git diff --cached antes do commit. Inclua os arquivos
   novos de services, migrations, scripts, templates/static, Dockerfile,
   requirements, package-lock.json e render.yaml. Há mudanças locais anteriores
   que também fazem parte do funcionamento atual.
4. Não envie .env, .env.neon.local, instance, bancos, backups ou planilhas com
   dados privados. O .gitignore/.dockerignore os exclui; isso não remove segredos
   que já tenham sido versionados no passado. Revise o CSV já versionado antes
   de tornar qualquer repositório público.
5. Instale no ambiente Python local (o Gunicorn será usado somente no Linux):
   
   ~~~powershell
   .venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-production.txt
   ~~~

## 4. Criar o Neon Free

1. No Neon, crie um projeto no plano **Free**, com PostgreSQL 17 ou 18 e região
   próxima do Render (Virginia/US East quando disponível).
2. Use um banco novo e exclusivo para este sistema. Mantenha scale-to-zero
   habilitado. Não habilite serviços extras pagos.
3. Em Connect, obtenha duas strings:
   - **Direta**, sem -pooler no host, para migração, manutenção e pg_dump.
   - **Pooled**, com -pooler no host, para a aplicação Render.
4. Mantenha sslmode=require e os demais parâmetros fornecidos pelo Neon.
   A aplicação aceita postgres://, postgresql:// e postgresql+psycopg://,
   seleciona psycopg 3 e exige TLS em produção. Não use sslmode=disable.
5. No computador, crie **.env.neon.local**, privado, com:

   ~~~dotenv
   APP_ENV=production
   SECRET_KEY=COLE_UMA_CHAVE_ALEATORIA
   DATABASE_URL=COLE_A_URL_DIRETA_DO_NEON
   MIGRATION_DATABASE_URL=COLE_A_MESMA_URL_DIRETA_DO_DESTINO
   RATELIMIT_STORAGE_URI=memory://
   RATELIMIT_SINGLE_PROCESS=true
   FEATURE_PARTICIPANTE_LOGIN=false
   ~~~

   Gere a SECRET_KEY uma vez com:

   ~~~powershell
   .venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
   ~~~

   A string de conexão contém senha. Não a cole em commits, screenshots, chats
   ou argumentos de terminal. O arquivo privado não substitui o .env local:
   cada comando remoto o lê explicitamente. Use a mesma chave estável no Render.

## 5. Escolher: migrar os dados atuais OU começar vazio

### A. Migrar o SQLite existente (recomendado)

Não execute inicializar no Neon antes de migrar: o importador exige um schema
public completamente vazio. Uma branch copiada de outra com tabelas não é vazia.
Use banco/projeto novo dentro das quotas Free. Não há opção --force ou --clean.

1. Identifique o arquivo SQLite usado pelo .env local; o padrão é
   instance/banco.db. Não modifique o banco original. Para ensaiar migrações de
   schema legado, crie uma cópia de trabalho:

   ~~~powershell
   .venv\Scripts\python.exe -m scripts.backup_banco instance/banco.db instance/para-neon.db
   ~~~

   O destino não pode existir. Guarde também uma cópia externa privada.
2. Se o schema ainda for antigo, atualize **essa cópia** seguindo
   MIGRACAO_FASE1.md, MIGRACAO_PARTICIPACAO.md e AJUSTES_PALPITES_SYNC.md,
   nesta ordem. Os IDs de administradores/responsáveis da Fase 1 devem ser
   revisados explicitamente, nunca aceitos cegamente. Os scripts antigos
   continuam exclusivos de SQLite e não devem ser executados contra PostgreSQL.
   Se a cópia já está atualizada, nenhuma migração legada é necessária.
3. Faça o ensaio local. Este comando não conecta ao Neon:

   ~~~powershell
   .venv\Scripts\python.exe -m migrations.sqlite_para_postgres instance/para-neon.db --backup instance/ensaio-neon.db
   ~~~

   Ele cria uma cópia consistente, valida integridade/referências, schema,
   booleanos, datas, inteiros e tamanho de textos. Mostra contagens e hashes,
   sem imprimir os registros. Não trunca textos nem corrige dados silenciosamente.
   Corrija incompatibilidades conscientemente na cópia e repita com novo nome.
4. Para a migração definitiva, interrompa novos lançamentos no sistema local.
   Faça uma nova cópia atualizada; não use um ensaio que ficou desatualizado.
   Com Render ainda não publicado (ou em manutenção), execute:

   ~~~powershell
   .venv\Scripts\python.exe -m migrations.sqlite_para_postgres instance/para-neon.db --backup instance/envio-neon.db --env-file .env.neon.local --aplicar
   ~~~

5. O importador cria tabelas, insere dados na ordem das referências, ajusta
   sequências e compara todas as linhas por contagem e SHA-256 na mesma transação.
   Falha de constraint ou de comparação reverte tabelas e registros criados.
   IDs, senhas já criptografadas, convites, participações, jogos, palpites,
   resultados, bônus, cache e logs são mantidos. O histórico técnico
   _schema_migrations fica preservado no SQLite de backup, não é reaplicado no
   PostgreSQL. Tabelas desconhecidas provocam recusa em vez de serem descartadas.
6. Guarde o relatório exibido e o backup. Se cair a conexão exatamente no commit,
   confira o destino antes de repetir: uma nova execução recusa tabelas existentes,
   mesmo vazias. Não apague o destino para tentar novamente sem verificar.
7. Entre com suas credenciais existentes após publicar. Confira os totais e
   rankings contra o SQLite. Não volte a lançar simultaneamente no SQLite:
   ele agora é cópia histórica, não sincroniza com Neon. Mantenha o original
   até concluir a conferência e o primeiro backup PostgreSQL.

Para testar antes do corte definitivo, use outro banco Neon vazio e depois
repita a migração final em um destino vazio separado. Isso também deve respeitar
as quotas gratuitas. O importador carrega o snapshot em memória e foi pensado
para o tamanho pequeno deste sistema.

### B. Começar sem dados

Se deseja um sistema vazio, execute no computador:

~~~powershell
.venv\Scripts\python.exe -m scripts.nuvem --env-file .env.neon.local inicializar
.venv\Scripts\python.exe -m scripts.nuvem --env-file .env.neon.local criar-admin
~~~

O segundo comando solicita email, nome e senha sem exibir a senha. Exige ao menos
12 caracteres e recusa email existente. Pode também criar outro administrador
após uma migração, caso necessário. Não habilite cadastro público para criar a
primeira conta.

O comando inicializar não apaga dados e não altera schemas antigos. Ele cria
schema novo explicitamente ou valida o existente. O servidor de produção não
cria/zera o banco automaticamente durante deploys.

## 6. Publicar a aplicação no Render Free

1. No Render, **New → Web Service**, conecte o repositório e selecione Docker.
   Se houver monorepo, Root Directory deve ser bolao2 (a pasta do Dockerfile).
2. Escolha instância **Free**, região próxima do Neon, uma única instância.
   Não crie disco ou serviço de banco. Não configure pre-deploy command.
3. Use o Dockerfile existente. Ele compila CSS/Alpine com npm ci e instala as
   dependências Python de produção. O comando de início já está na imagem.
   A porta é lida de PORT fornecida pelo Render.
4. Desative auto-deploy para controlar mudanças e consumo de builds. Configure
   Health Check Path como **/healthz**.
5. Cadastre as variáveis abaixo:

   | Variável | Valor |
   | --- | --- |
   | APP_ENV | production |
   | SECRET_KEY | A chave aleatória privada e estável gerada antes |
   | DATABASE_URL | URL **pooled** Neon, com TLS |
   | RATELIMIT_STORAGE_URI | memory:// |
   | RATELIMIT_SINGLE_PROCESS | true |
   | FEATURE_PARTICIPANTE_LOGIN | false |
   | TRUST_PROXY | true |
   | TRUSTED_HOSTS | Hostname exato onrender.com, sem https:// nem caminho |
   | SYNC_ENABLED | false |
   | FLASK_DEBUG | 0 |
   | FOOTBALL_DATA_TOKEN | Opcional; token gratuito da API, se utilizado |

   Remova REDIS_URL, RATELIMIT_STORAGE_URL e PERSISTENT_DATA_DIR de uma
   configuração antiga. Mantenha SECRET_KEY fora do código; trocá-la desconecta
   sessões. O app não precisa de MIGRATION_DATABASE_URL em produção.
6. Alternativamente, use **New → Blueprint** com render.yaml. Ele contém
   somente uma web Free e solicita DATABASE_URL; gera SECRET_KEY. Se o painel
   exigir pagamento para esse caminho, use a criação manual Free acima.
7. Aguarde deploy. /healthz deve responder 200; visite **/readyz uma vez**
   para comprovar acesso ao Neon. Confira o host em TRUSTED_HOSTS após conhecer
   a URL definitiva; vários hosts podem ser separados por vírgula.
8. Acesse /login. Confirme login, bolões, permissões administrativas, lançamento,
   resultados, ranking, importação XLSX e recursos de API que você usa. O link
   fica acessível pela internet, mas as áreas privadas continuam autenticadas.
9. Faça um redeploy e confira os registros: permanecem no mesmo banco Neon.
   Se o banco estiver indisponível, o app não cria SQLite substituto.
10. Somente depois divulgue https://SEU-SERVICO.onrender.com aos administradores.

Se já existir um serviço pago da configuração anterior, ele continuará sendo
cobrado até você removê-lo/downgrade no painel. Antes de excluir discos/Redis ou
o serviço antigo, migre e faça backup dos dados. Este trabalho não alterou nem
contratou recursos remotos.

## 7. Recursos que precisam de atenção

- Upload de planilha funciona pelo navegador. Seleção de arquivo na pasta
  Downloads procura arquivos no servidor, não no Windows do administrador;
  prefira upload. O arquivo original deve ficar guardado com você.
- SYNC_ENABLED=true mantém o worker existente, mas só enquanto a web estiver
  ativa. Não há cron gratuito confiável incluído; use Admin → Sincronizar.
- Fontes externas, API e escudos remotos dependem dos respectivos serviços.
  CSS, Alpine e escudos locais vêm na imagem.
- Dates dos jogos continuam em horário de Brasília sem offset, como no SQLite.
  Comparações passaram a usar Brasília explicitamente, mesmo com servidor UTC.
  Datas de auditoria continuam UTC.
- Conexões PostgreSQL usam pool pequeno, reconexão preventiva e timeout.
  O cold start do Neon pode atrasar a primeira consulta.
- Cookies Secure/HttpOnly/SameSite, CSRF, hashes e permissões foram mantidos.
  TRUST_PROXY=true confia em um salto do proxy Render; não copie isso para
  servidor diretamente exposto ou outra cadeia de proxies sem revisão.
- Limite global atual de 50/h e 200/dia por IP permanece; administradores na mesma
  rede compartilham limite. A recuperação pública de senha continua desativada.
- O modelo de entrada é gestão por administradores/responsáveis existentes.
  FEATURE_PARTICIPANTE_LOGIN=false bloqueia o fluxo de cadastro/participante;
  não muda os papéis ou amplia permissões de contas importadas.

## 8. Backup e restauração do PostgreSQL

Persistência significa que atualizar/reiniciar o Render não apaga Neon. Não
significa proteção contra exclusão do projeto, erro humano ou todas as políticas
futuras do serviço. Não dependa apenas da curta janela de recuperação gratuita
do provedor.

Instale os clientes oficiais PostgreSQL (pg_dump e pg_restore) no computador.
Use versão igual ou mais nova que a versão do servidor; esses programas são
gratuitos. Com conexão **direta**, faça backup antes de atualizações e regularmente,
conforme a frequência dos lançamentos. Exemplo em PowerShell:

~~~powershell
$env:PGSSLMODE = "require"
$env:PGCHANNELBINDING = "require"
pg_dump --host=HOST_DIRETO_NEON --port=5432 --username=USUARIO_NEON --dbname=NOME_BANCO --password --format=custom --no-owner --no-acl --file=backup-2026-10-12.dump
Get-FileHash backup-2026-10-12.dump -Algorithm SHA256
~~~

A senha será solicitada; não coloque a string completa com senha na linha de
comando. Confira código de saída 0 e arquivo criado. Guarde uma cópia privada
fora do computador e fora do Neon, usando armazenamento gratuito que você já
possua. O dump contém dados pessoais e hashes; não o versione.

Para ensaiar restauração, crie um banco PostgreSQL vazio separado, no Free:

~~~powershell
pg_restore --host=HOST_DIRETO_NEON --port=5432 --username=USUARIO_NEON --dbname=BANCO_NOVO_VAZIO --password --single-transaction --exit-on-error --no-owner --no-acl backup-2026-10-12.dump
~~~

Use o mesmo TLS. Não adicione --clean. Valide a cópia restaurada antes de
redirecionar a aplicação. Se houver tabelas conflitantes, a restauração aborta
e a transação é revertida. Uma restauração perde alterações posteriores ao backup;
preserve o estado atual antes de qualquer troca.

O comando scripts.backup_banco e o CLI backup-banco são somente para SQLite.
Eles não fazem backup do Neon. Nenhum backup externo agendado foi contratado
ou criado automaticamente nesta preparação.

## 9. Atualizações futuras sem apagar dados

1. Rode testes localmente; faça pg_dump e mantenha cópia externa.
2. Envie o novo código ao GitHub e use Manual Deploy no Render.
3. Mantenha a mesma DATABASE_URL, projeto/banco Neon e SECRET_KEY. O Dockerfile
   contém somente código/estáticos, nunca os dados.
4. Para alteração de schema PostgreSQL, prepare uma migração SQL versionada,
   compatível e testada em cópia. As migrações legadas da pasta migrations são
   SQLite específicas; o importador novo é de transferência inicial, não de upgrade.
5. Durante alteração estrutural, configure MAINTENANCE_MODE=true no Render e
   aguarde o deploy; isso suspende acesso funcional e worker. Execute a migração
   pelo computador com conexão direta. Valide e desative manutenção.
6. Não rode novamente o importador sobre produção já preenchida, nem comandos
   DROP/TRUNCATE/reset. A aplicação só valida o schema ao iniciar; não faz ALTER.
7. Em falha, mantenha manutenção, preserve o estado atual e restaure backup em
   outro banco vazio. Só troque a URL após conferir dados e compatibilidade
   com a versão do código. Rollback do código não desfaz alterações no banco.

## 10. Desenvolvimento e validação

O .env de desenvolvimento continua com APP_ENV=development, SQLite local e
limiter em memória. A instalação básica e python app.py continuam funcionando.
Para preparar a interface: npm ci e npm run build:css.

~~~powershell
.venv\Scripts\python.exe -m pytest -q
~~~

Testes PostgreSQL adicionais usam somente um cluster **local descartável** via
TEST_POSTGRES_URL, nunca a URL Neon real. Criam bancos com nomes bolao_test_*
e os deixam para inspeção; destrua somente o cluster descartável quando terminar.
Sem essa variável, os testes de integração PostgreSQL são marcados como ignorados.

O workflow manual .github/workflows/deploy-check.yml testa com PostgreSQL 17 no
Linux e constrói o Dockerfile. Não realiza deploy. Na preparação local foram
testados PostgreSQL 18, importação/conferência integral, recusa de destino ocupado,
rollback de tabelas/dados após erro, sequências, senha migrada, gestão e auditoria.
Resultado local: **340 testes passaram** (incluindo PostgreSQL), build CSS/Alpine
concluído e pip check sem conflitos. Permanecem avisos de APIs legadas existentes.
Depois das últimas proteções de schema, a suíte direcionada passou em 30 testes,
incluindo dois novos casos de banco vazio/parcial (342 casos no total do projeto).
O deploy Linux/Render e o TLS real do Neon ainda exigem a conferência da etapa 6.


## 11. Bolões e campeonatos — preparação de outubro de 2026

Cada novo bolão é criado junto com seu campeonato e temporada, na tela
**Criar bolão**. Dois bolões podem usar o mesmo nome de competição e ano,
mas mantêm campeonatos e jogos independentes. Não é mais possível cadastrar
um campeonato avulso pela interface nem criá-lo durante a importação Excel.
Abra o bolão e importe a planilha no campeonato dele. O código mantém a leitura
de registros legados; essa alteração não exige mudança de esquema SQL.

A limpeza solicitada foi uma operação local pontual, com backup, preparação
em banco separado e conferência antes da substituição. Não há limpeza automática
no startup, no deploy ou em reinicializações. Para publicar os dados atualizados,
use o procedimento de migração deste documento com o SQLite atual; não importe
um backup anterior à limpeza. Guarde os backups privados fora do Git.

Validação desta alteração: suíte existente com 339 aprovados e 3 integrações
PostgreSQL ignoradas (servidor local desligado); após acrescentar seis regressões,
44 testes direcionados aprovados. Build de CSS/Alpine concluído.

Atualização do ranking: Acertos conta vencedor/empate correto sem placar exato,
calculado dos palpites válidos e resultados dos jogos. Não usa os contadores
inconsistentes do resumo Excel. No celular, cada participante tem seus pontos,
cravadas e acertos visíveis em um cartão. Em desenvolvimento, os templates
recarregam automaticamente mesmo sem habilitar o depurador.

Última verificação local: 346 testes aprovados, 3 integrações PostgreSQL
ignoradas por ausência do servidor de teste; build CSS concluído. Servidor
local reiniciado e resposta HTTP do ranking conferida. A publicação no Render
foi concluída em 12/10/2026, com os dados migrados para Neon e conferidos integralmente.


## 12. Instalação publicada

- Site: https://bolao-brasileirao-3r4o.onrender.com
- Repositório privado: https://github.com/Mitzspace/bolao-brasileirao
- Branch de publicação: `codex/publicacao`.
- Render: https://dashboard.render.com/web/srv-db6mvs8u01pc73feg7t0
- Serviço Docker Free, Ohio, health check `/healthz`, atualizações manuais.
- Neon: projeto `Bolão Brasileirão`, plano Free, região AWS Ohio, branch `production`.
- Versão inicial: `1188c0f`. Contém o ranking corrigido e a visualização móvel de Acertos.
- Migração inicial: 24 participantes, 38 rodadas, 380 jogos, 5.806 palpites e 289 resultados.
- William e Ryan preservam suas contas, hashes de senha e permissões administrativas.

Os dados online passam a ser os oficiais. O SQLite local é independente: editar
nele não atualiza o site, e alterações online não voltam automaticamente para ele.
Não execute novamente a importação inicial para atualizar o sistema.

### Atualizar código sem perder dados

O primeiro envio foi preparado numa cópia limpa em `instance/publicacao`, para
não enviar histórico anterior, dados ou credenciais. O projeto original continua
na pasta principal, com suas alterações locais preservadas.

1. Faça e teste as alterações no projeto principal.
2. Copie somente os arquivos de código alterados para `instance/publicacao`,
   mantendo as mesmas subpastas. Remoções e novos arquivos devem ser revisados
   explicitamente. Não copie `.env*` privados, `instance`, planilhas ou bancos.
3. Dentro de `instance/publicacao`, confira `git diff` e `git status`, adicione
   somente os arquivos revisados, faça commit e envie com `git push`.
4. No Render, use **Manual Deploy → Deploy latest commit**. Aguarde **Live**.
5. Verifique `/healthz`, `/readyz`, login, administração e ranking.

O deploy substitui o código, mas mantém o banco Neon. Não altere `DATABASE_URL`
para outro banco. Mudanças de esquema exigem backup e migração específica conforme
a seção 9. Os arquivos `.env.neon.local` e `.env.render.local` ficam apenas neste
computador e estão excluídos do Git; guarde-os com segurança.

No plano gratuito, o Render suspende o serviço após inatividade e o primeiro
acesso pode demorar cerca de um minuto ou mais. O computador local pode ficar
desligado. Não há garantia de disponibilidade contínua do plano Free. Não ative
upgrades, discos, workers ou planos pagos; os dados persistem no Neon, não no
sistema de arquivos efêmero do Render.
