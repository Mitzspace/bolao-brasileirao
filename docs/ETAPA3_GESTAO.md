# Etapa 3 — URLs, permissões e responsáveis

Branch de trabalho: `codex/gestao-admin-etapa1`, preservando as etapas anteriores.
Sem migração ou modificação do banco em uso.

## URLs no modo de gestão

Os endpoints usados por `url_for` e os nomes de campos dos formulários existentes
foram mantidos. As URLs geradas passam a conter o ID do bolão:

| Caminho anterior | Caminho canônico |
| --- | --- |
| `/` | `/b/<id>/` |
| `/admin/` | `/b/<id>/gestao` |
| `/admin/palpites` | `/b/<id>/palpites` |
| `/ranking` | `/b/<id>/ranking` |
| `/tabela` | `/b/<id>/tabela` |
| `/jogos` e `/jogos/<rodada_id>` | Mesmos sufixos sob `/b/<id>` |
| `/rodada/<rodada_id>/palpites` | Mesmo sufixo sob `/b/<id>` |
| `/admin/participantes` | `/b/<id>/participantes` |
| `/admin/resultados` | `/b/<id>/resultados` |
| Nova tela `/admin/responsaveis` | `/b/<id>/configuracoes` |
| Demais rotas `/admin/<sufixo>` | `/b/<id>/<sufixo>` |

Os caminhos antigos continuam registrados. GET/HEAD redirecionam com 302 e POST
com 307, preservando método e corpo. A gravação acontece somente no destino.
Sem contexto suficiente, o usuário é encaminhado para escolher o bolão.
IDs contraditórios na URL, query string ou formulário são recusados.
O fluxo de palpite próprio permanece desativado pela flag da Etapa 1.
Ao reativar a flag, a geração de URLs e navegação legadas continua disponível.

## Troca e escopo

- Seletor por toque/clique (`details`/`summary`), com nome, campeonato e temporada.
- Palpites e resultados mantêm a rodada quando o campeonato é o mesmo; o filtro
  de participante não é transferido. A grade escolhe uma rodada do campeonato
  de destino quando necessário; sem jogos, volta ao início.
- Todas as requisições no modo de gestão exigem participação ativa como
  responsável no bolão acessado, inclusive para administradores globais.
- Jogos, rodadas e campeonatos informados em caminhos e formulários
  administrativos são conferidos contra o campeonato do bolão.
- Listas administrativas são limitadas ao contexto. A tela de participantes
  passa a consultar Participacao, incluindo registros sem conta.
- Sincronização, importadores legados, criação de campeonato e manutenção de
  contas legadas ficam restritos ao administrador global. Os serviços de API e
  importação não foram reescritos. CRUD completo de participações fica para a
  próxima etapa; os handlers legados não foram apagados.

## Responsáveis

Em Configurações, é possível adicionar uma conta existente por e-mail ou criar
uma nova conta com nome, e-mail e senha inicial. A permissão é concedida apenas
ao bolão atual. Contas existentes mantêm nome, senha e permissões globais.
Um registro legado compatível é reaproveitado para preservar seu histórico;
vínculos ambíguos são recusados com 409.

Remover acesso muda o papel para participante, sem apagar participação, conta,
palpites ou logs. Remover o próprio acesso encerra a sessão. A última conta ativa
com senha e papel de responsável não pode ser retirada. Um responsável sem conta
habilitada não conta como substituto. As mutações são serializadas por bloqueio
de escrita no bolão; a autorização é revalidada depois do bloqueio. O caminho
legado de remoção de participante usa a mesma proteção no modo de gestão.

## Validação

- 184 testes aprovados; 23 novos casos da Etapa 3.
- Cobertura de URLs entre abas, redirecionamento POST sem gravação dupla,
  CSRF, IDs de outro campeonato, campos contraditórios, troca de rodada,
  adição/remoção, acesso revogado e proteção do último responsável habilitado.
- Em cópia dos dados atuais: nove telas canônicas, redirecionamento legado,
  criação e remoção de acesso de responsável; 5.652 palpites e 5.652 logs preservados.
- SHA-256 do banco original idêntico antes/depois. Não houve chamada à API real.

A Etapa 4 aguarda confirmação: criação de bolão com cópia seletiva de participantes
e conclusão da gestão de participações sem conta, incluindo reativação.
