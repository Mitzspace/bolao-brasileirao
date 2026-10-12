Seleção de bolão e ordem dos palpites
===================================

“Meus palpites” ordenava o nome da rodada como texto. Isso colocava a 10ª rodada
antes da 1ª. A ordenação agora usa o número da rodada. A conferência do banco real
confirmou 10 palpites de William em cada rodada da 1ª à 9ª; nenhum estava perdido.

O cabeçalho compartilhado mostra nome do bolão, campeonato, criador e uma chave
pública estável (`BOL-000001` para o bolão existente). A chave deriva da chave
primária de Bolao, que já é única no banco; não houve alteração de schema nem
migração. O código aleatório de convite continua separado e não aparece no menu.

A seleção fica na sessão e exige participação ativa vinculada ao usuário,
inclusive para o administrador global. A partir da etapa 1 de navegação, as
páginas do bolão exigem login. Saída/remoção revoga o acesso, preservando os dados
históricos para os participantes autorizados.

Meus palpites, ranking, grade e lançamentos administrativos consultam participação
e bolão, inclusive quando dois bolões compartilham o mesmo campeonato e jogo.
Jogos e classificação usam o campeonato do bolão selecionado. Nomes das rotas e
campos existentes foram preservados. No lançamento administrativo, participante_id
agora identifica a Participacao; os IDs da migração existente coincidem com os IDs
legados, mantendo a seleção atual. Formulários próprios levam também bolao_id para
recusar envio se o usuário tiver trocado de contexto em outra aba.

Resultados, manutenção de campeonatos e sincronização continuam dados globais.
Quando houver vários bolões, a administração legada de contas e manutenção fica
restrita ao administrador global; responsáveis mantêm dashboard e lançamento por
participação. A gestão por participação será ampliada na Fase 2. Criação pública
de bolão e links de ingresso continuam previstos na Fase 5.

Validação anterior: 87 testes passaram; cenários incluem bolões com mesmo nome, criador e
campeonato, troca de campeonato, isolamento de leitura/gravação e rejeição de
seleção sem autorização. Prévia desktop/celular e 26 telas existentes verificadas
com cópia do banco. O banco original permaneceu intacto.

Etapa 1 de navegação — seleção e bolão ativo
------------------------------------------

Branch: `codex/selecao-navegacao-boloes`, criada preservando as alterações locais.

`GET /boloes` mostra os cartões com nome, campeonato, temporada, criador e chave
pública. A tela permanece acessível mesmo quando já há um bolão selecionado.
Login e cadastro redirecionam para `/boloes?continuar=1`: uma seleção lembrada
válida ou uma única participação ativa leva diretamente ao início do bolão.
Sem participação ativa, a página explica que o responsável deve vincular a conta.
Ainda não existe fluxo de ingresso por convite; por isso não há botão sem destino.

O POST `/boloes/selecionar`, o endpoint `participante.selecionar_bolao` e o campo
`bolao_id` foram mantidos. Novo endpoint: `participante.escolher_bolao`.
Nenhum caminho anterior foi substituído. Nas rotas dependentes, `?bolao_id=ID`
tem precedência sobre a sessão e exige autorização; valores inválidos, duplicados
ou sem participação ativa retornam 403, sem fallback para outro bolão.
Sem contexto válido, usuários autenticados voltam à escolha e anônimos ao login.

O contexto é revalidado antes de executar as rotas de participante e administração.
A seleção e a última escolha são associadas ao ID do usuário na sessão. Logout
remove o contexto ativo, preservando a última escolha; outra conta não a herda.
Essa lembrança depende da existência do cookie de sessão e não é entre dispositivos.
Não foram alterados models, schema, pontuação, sincronização nem prazos.

O context processor e o before_request existentes foram reaproveitados. Ao final
da etapa 1, links antigos ainda usavam a sessão; somente URLs com `bolao_id`
explícito fixavam o contexto entre abas (ampliado na etapa 2 abaixo). O seletor de
rodada fica para a etapa 4. Criação de bolões e configurações de conta terão planos
próprios depois dessas quatro etapas.

Validação desta etapa: 109 testes, incluindo acesso revogado, troca de conta,
admin global sem participação, seleção automática, última escolha, IDs inválidos,
contexto por URL e CSRF. Os testes de Tabela/Grade/Ranking agora usam autenticação,
mantendo as verificações de cache, privacidade e desempate. CSS compilado localmente.
Conferência adicional em cópia SQLite: seleção automática e Meus palpites nas duas
contas vinculadas ativas; 24 participantes, 38 rodadas, 380 jogos, 5.652 palpites,
279 resultados e 60 pontos de bônus. Hash SHA-256 do original igual antes/depois.

Etapa 2 de navegação — contexto e menu condicional
------------------------------------------------

O context processor compartilha os objetos já carregados e validados na requisição.
Renderizar o menu e o seletor não repete consultas de bolões, campeonato, criador
ou participação. O estado de responsável exige um bolão ativo e participação ativa,
inclusive para administrador global.

Menus desktop e celular ocultam Jogos, Tabela, Ranking, Meus palpites e Admin
quando não há bolão ativo. Usuários autenticados têm acesso a Meus bolões e Sair;
visitantes têm Entrar e Cadastrar. O logo leva à seleção ou ao login quando não
existe contexto. O submenu administrativo também exige contexto e responsabilidade.

Um callback de url_defaults acrescenta bolao_id aos links, ações e redirecionamentos
gerados por url_for para as rotas dependentes, preservando IDs explícitos. Rotas de
autenticação, seleção e arquivos estáticos não recebem o parâmetro. Os caminhos,
endpoints e campos anteriores permanecem iguais. O filtro GET administrativo de
palpites ganhou um campo oculto bolao_id para preservar o contexto no envio.
Links antigos sem parâmetro continuam usando a seleção válida da sessão.

Validação: 116 testes passaram, incluindo navegação entre abas com bolões distintos,
menu sem seleção para administrador global, permissões do menu administrativo,
ausência de consultas extras na renderização e preservação do filtro administrativo.
Menus desktop/celular foram conferidos no HTML renderizado das duas contas vinculadas
em cópia do banco atual; hash do original permaneceu igual. Não houve nova inspeção
visual em navegador nesta etapa. Pontuação, API e models não foram alterados.

Etapa 3 de navegação — dropdown no cabeçalho
------------------------------------------

O seletor fica no cabeçalho compartilhado, inclusive em Meus palpites. O controle
nativo details/summary abre por clique, toque ou teclado; Alpine acrescenta Escape
e clique fora. O painel tem altura limitada com rolagem e largura adaptada ao celular.
Exibe nome, campeonato, temporada, criador, chave pública e Ver todos os bolões.

O POST de seleção mantém bolao_id e CSRF. Campos adicionais: aba_origem,
bolao_origem_id e rodada_origem_id nas páginas de rodada. O servidor constrói o
destino a partir de endpoints permitidos; não aceita URLs livres. Origem e destino
exigem participação ativa. A origem explícita independe da seleção em outra aba.

Ranking, Tabela, Jogos e Meus palpites mantêm sua aba. Jogos mantém a rodada no
mesmo campeonato; em outro campeonato abre Jogos sem a rodada antiga. Grade e
formulário de rodada exigem rodada válida do mesmo campeonato; senão abrem o início.
Formulário de rodada fechada também volta ao início. Telas administrativas sem IDs
de recursos são mantidas somente quando autorizadas, sem transferir filtros antigos.
Edição de recursos, destinos desconhecidos e falta de permissão voltam ao início.

Validação: 135 testes passaram; CSS recompilado. Dropdown conferido no navegador
em 390×844 e 1280×800 com dados fictícios em memória. Troca em Meus palpites e
Ver todos os bolões funcionaram. Conferência nas duas contas vinculadas em cópia
do banco real; hash do original preservado. Prévia: instance/seletor-etapa3-desktop.png.
Pontuação, models e sincronização não alterados.

Próxima etapa: seletor de rodada em Meus palpites, sujeito à confirmação. Preservar
a rodada nessa aba será implementado junto com seu filtro na etapa 4.
