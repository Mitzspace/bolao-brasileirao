# Correções aplicadas — 12/10/2026

Validação após a preparação de Redis: **319 testes passaram**, com 129 avisos,
em 76,45 segundos. Os testes do Redis usam respostas simuladas; nenhuma conexão
com serviço de produção foi testada.
`git diff --check` não identificou erros de whitespace. Os dois comandos de
importação responderam corretamente a `--help`, sem executar importações reais.

Após a autorização para corrigir, foram implementados:

- Desativação da redefinição pública de senha sem comprovação de posse da conta.
  A tela orienta a procurar o administrador; não há promessa de envio de e-mail.
- Chave correta `RATELIMIT_STORAGE_URI`, com compatibilidade para o nome antigo,
  e seleção explícita de ambiente por `APP_ENV`. Produção recusa a chave padrão
  de desenvolvimento e não habilita o debugger.
- Validação de datas, nomes, temporadas, IDs e placares antes de gravar; palpites
  próprios são validados como lote para não salvar parcialmente uma requisição inválida.
- Restauração dos imports da API e correção da atualização de jogos existentes.
- Importação de planilhas com rollback, mensagem genérica de erro, leitura de
  uploads por stream e seleção local restrita à pasta configurada.
- Carregamento antecipado de palpites, jogos, resultados e bônus no ranking,
  grade e meus palpites, com teste de quantidade de consultas no ranking.
- Importadores CLI unificados, parâmetros explícitos e parser compartilhado,
  incluindo formatos de placar entre colchetes e bônus da aba TOTAL. Os scripts
  criam um novo campeonato e preservam o histórico; não executam reset.
- Hash real nas fixtures, remoção dos tokens CSRF fictícios e dependências
  diretas Python fixadas nas versões do ambiente testado.
- Mensagem de login em português e atualização de README e `.env.example`.

Não foi necessário alterar o schema, executar migrações ou modificar o banco
real. A variável de ambiente do backend compartilhado do limiter deve ser
configurada no ambiente de produção; nenhum servidor Redis foi provisionado.

Preparação adicional autorizada: criado modelo `.env.production.example`,
dependências em `requirements-production.txt` e guia `DEPLOY_REDIS.md`.
Produção recusa `memory://`; a configuração também aceita `REDIS_URL`.
O comando `flask --app wsgi:app verificar-limiter` testa a conexão sem imprimir
credenciais. A hospedagem ainda não foi definida, portanto Redis real não foi
conectado nem provisionado.

As sugestões opcionais de adotar FlaskForm/Alembic, padronizar retornos dos
validadores antigos e mover arquivos da raiz não foram tratadas como bugs.
As migrações próprias e as assinaturas existentes foram preservadas.

## Diagnóstico anterior (histórico, antes das correções)

# Validação da lista de correções — 12/10/2026

Escopo: estado local atual de `bolao2`, incluindo alterações ainda não commitadas. O documento recebido foi tratado como uma lista de alegações para conferir, não como autorização para implementar seu plano. Nenhum código de aplicação foi alterado. O arquivo `.env` e o banco real não foram inspecionados; as reproduções usaram SQLite em memória.

## Falhas que merecem prioridade

1. **Armazenamento do limiter incorreto** — `config.py:56` define `RATELIMIT_STORAGE_URL`, mas a versão instalada lê `RATELIMIT_STORAGE_URI`. A instância única funciona: em um teste isolado com o limiter habilitado, a 11ª consulta a `/login` retornou 429. Entretanto, o backend caiu em `MemoryStorage`; configurar a variável documentada não seleciona armazenamento compartilhado. Limites em memória não são compartilhados entre processos e se perdem no reinício.
2. **Entradas inválidas ainda causam exceções** — `routes/admin.py:590`, `:622`, `:691` e `:692`: datas/placares são convertidos sem tratamento. Reproduzi `ValueError` para data inválida e placar `abc` chamando os corpos das rotas em contexto de requisição de teste. `routes/participante.py:259` também mantém conversões diretas, mas esse fluxo depende de `FEATURE_PARTICIPANTE_LOGIN=true`. Campos ausentes em `request.form[...]` normalmente produzem HTTP 400, não necessariamente 500 como sugere a lista.
3. **Importações de jogos/resultados quebradas** — `routes/admin.py:736` e `:810` chamam `buscar_jogos_football_data` e `buscar_resultados_football_data`, mas os nomes não estão importados. Reproduzi os dois `NameError`, sem chamar a API. A alegação de que esses imports seriam inúteis estava errada. Há também referência a `jogo` sem atribuição no ramo de jogo já existente (`:765`).
4. **Detalhes internos expostos** — `routes/admin.py:1201` continua mostrando `str(e)` ao falhar a importação de planilha.
5. **Seleção do ambiente ainda depende de FLASK_ENV** — `app.py:22` escolhe desenvolvimento por padrão. Definir apenas `FLASK_DEBUG=0` não seleciona `ProductionConfig` nem seus cookies seguros. Não basta remover a variável: é necessário definir um seletor explícito de configuração.

**Achado adicional, fora da lista:** `routes/auth.py:117–135` permite redefinir a senha de uma conta para `123456` apenas informando o e-mail, sem comprovar posse da conta. A rota não está na lista de rotas desativadas em `services/acesso.py`. CSRF não substitui essa comprovação. Prioridade máxima antes de expor a aplicação; usar recuperação por token ou desativar o reset simplificado. Este achado foi conferido por leitura, sem redefinir contas reais.

## Conferência dos 25 itens

| Item | Situação atual | Evidência / interpretação |
|---|---|---|
| 1. Limiter duplicado | Parcialmente resolvido | Instância única em `extensions.py`, inicializada em `app.py` e usada por `routes/auth.py`. Limite confirmado; chave do backend ainda errada, conforme acima. Uma variável local, isoladamente, não provaria que uma extensão deixou de funcionar. |
| 2. Caminhos/e-mails fixos | Parcialmente resolvido | Uploads usam `app.instance_path`. Os dois scripts de importação ainda contêm caminhos e e-mail fixos; `routes/admin.py:1145` mantém pasta pessoal como fallback. |
| 3. `.env.example` ausente | Resolvido localmente | Arquivo existe, mas está não rastreado no Git. Não contém a configuração do armazenamento do limiter. Precisa ser incluído no commit para acompanhar o projeto. |
| 4. Sem migrações | Diagnóstico desatualizado | Existem migrações próprias versionadas 001/002, com backup, verificação e reversão. A aplicação recusa schemas antigos; `create_all()` ficou para banco sem tabela de participante. Não há Alembic/Flask-Migrate, e as migrações atuais são específicas de SQLite. Adotar Alembic é uma decisão de evolução, não ausência total de migrações. |
| 5. Validação de entradas | Ainda pendente em rotas antigas | Serviços novos validam diversos fluxos, mas datas e resultados administrativos mantêm conversões desprotegidas. Ver reproduções acima. |
| 6. Segurança de sessão | Essencial implementado | HTTPOnly, SameSite, duração e Secure em produção existem. `SESSION_REFRESH_EACH_REQUEST` já é True por padrão no Flask instalado. Não há `session.permanent=True`, portanto não se deve prometer persistência de sete dias apenas pela configuração de duração. Ver ressalva de seleção do ambiente. |
| 7. Duplicação dos importadores | Ainda pendente | Scripts continuam com implementações próprias de leitura e importação, embora exista `services/importador_planilha.py`. Consolidar se os scripts ainda forem mantidos. |
| 8. Sem FlaskForm | Sugestão opcional | Não encontrei classes FlaskForm. Validação manual não é defeito por si só; corrigir as validações faltantes é o requisito funcional. |
| 9. `debug=True` fixo | Resolvido no comando `python app.py` | `app.py` lê `FLASK_DEBUG` antes de `app.run`. A configuração do ambiente continua sendo uma questão separada. |
| 10. N+1 | Ainda pendente | `routes/participante.py:347` percorre `p.palpites`, jogos e resultados; há consulta de bônus por participante. Meus palpites (`:298`) e grade (`:158`) também acessam relações sem carregamento antecipado. O join de filtragem não carrega automaticamente essas relações. Não foi realizado benchmark de volume. |
| 11. Imports mortos | Lista parcialmente incorreta | `generate_password_hash` foi removido de auth; HTTPError/URLError são usados, sem a duplicação local citada. CSRFError é usado pelo handler do blueprint. Os dois imports da API foram removidos, mas as chamadas permanecem e falham. |
| 12. Imports tardios | Parcialmente resolvido; baixa prioridade | `datetime` está no topo de models; `from models import Jogo` continua dentro de `ver_grade_palpites`, redundante com o import do módulo. Imports locais não são necessariamente erros. |
| 13. Erros internos na interface | Ainda pendente | `routes/admin.py:1201` mostra a exceção da planilha ao usuário. |
| 14. E-mail em scripts | Parcialmente resolvido | `primeiro_acesso.py` recebe e-mail por argumento. `reset_e_importar_oficial.py` mantém e-mail fixo. |
| 15. Sem testes admin | Diagnóstico desatualizado | Há testes de gestão, responsáveis, participantes, lançamento, acesso e exclusão. Ainda faltam casos que detectem os erros de importação e entradas inválidas encontrados nesta revisão. |
| 16. CSRF fictício nos testes | Ainda presente | `tests/test_auth.py` envia `csrf_token="test"` com CSRF desligado. Existem também testes específicos com CSRF habilitado; não é correto dizer que toda a suíte ignora CSRF. |
| 17. Hash fictício nas fixtures | Ainda pendente | `tests/conftest.py:61` e `:76` mantêm `pbkdf2:sha256:260000$random$hash`. |
| 18. Dependências sem versões | Ainda pendente | `requirements.txt` continua sem versões ou lock Python. O package-lock do frontend não resolve a reprodutibilidade do backend. |
| 19. `app.run` em wsgi | Sugestão opcional | O bloco protegido por `if __name__ == "__main__"` continua presente e não executa quando o módulo é importado pelo servidor WSGI. |
| 20. FLASK_ENV | Ainda usado pelo projeto | A variável seleciona configuração explicitamente no código. Substituir com cuidado; `FLASK_DEBUG` sozinho não seleciona o ambiente de produção atual. |
| 21. API dos validadores | Sugestão de padronização pendente | Nome/e-mail retornam bool; senha retorna tupla. Os consumidores atuais tratam as assinaturas distintas. |
| 22. CSV na raiz | Ainda presente; organização | `pontuacoes_oficiais_bolao.csv` continua na raiz. Não é bug funcional. |
| 23. Compartilhar na raiz | Ainda presente; organização | `compartilhar.py` continua na raiz. |
| 24. Mensagem de login | Parcialmente resolvido; UX | Categoria `info` está definida; texto personalizado não. Flask-Login fornece mensagem padrão, portanto não há ausência total de mensagem. |
| 25. Pasta pessoal no fallback | Ainda pendente | Mesmo problema do item 2 em `routes/admin.py:1145`; não contar como defeito independente. |

## Validação

- Revisão estática dos arquivos correspondentes à lista e inspeção do código instalado de Flask/Flask-Limiter.
- Teste isolado de limite do login: dez respostas 200 seguidas de 429.
- Reproduções isoladas: duas conversões inválidas geram ValueError; duas importações geram NameError. As chamadas ao corpo das rotas não constituem teste completo de autenticação/permissões.
- Suíte completa: **277 testes passaram**, com 123 avisos, em 90,08 segundos. A primeira execução teve 262 aprovações e 15 erros de preparação por acesso negado à pasta temporária do pytest; a repetição autorizada fora do sandbox passou integralmente. A suíte atual não detecta os defeitos adicionais reproduzidos acima.

Nenhuma correção aplicada nesta revisão.
