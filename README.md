# Bolão v2

Sistema de bolão de futebol em Flask com sincronização automática via API football-data.org.

## Publicação na nuvem

Siga [DEPLOY.md](DEPLOY.md) para análise, custos, publicação no Render,
transferência do banco atual, backups e atualizações. O `render.yaml` prepara
Render Free com Neon PostgreSQL Free externo e limiter em memória, sem Redis.
Nenhum recurso remoto é criado
até você conectar o repositório e aprovar a criação no painel.

## 🚀 Melhorias de Segurança Implementadas

### 1. Gerenciamento de SECRET_KEY
- Validação de SECRET_KEY na inicialização
- Configurações separadas para desenvolvimento, produção e testes
- Chave aleatória gerada automaticamente em desenvolvimento
- Impede uso de chave de desenvolvimento em produção

### 2. Proteção CSRF
- Tokens CSRF adicionados em todos os formulários
- Proteção contra ataques de falsificação de requisição entre sites
- Página de erro 403 para erros de CSRF

### 3. Rate Limiting
- Limite global: 200 requisições por dia, 50 por hora
- Limite específico para cadastro: 5 por hora
- Limite específico para login: 10 por hora
- Página de erro 429 para limite excedido

### 4. Validação de Inputs
- Validação de email com regex
- Validação de senha (mínimo 6 caracteres)
- Validação de nome (mínimo 2 caracteres)
- Validação de extensão de arquivos upload
- Módulo `utils.py` com funções reutilizáveis

## 📦 Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações
```

## 🔧 Variáveis de Ambiente

```bash
SECRET_KEY=SEU_TOKEN_SECRETO_AQUI
DATABASE_URL=sqlite:///banco.db
FOOTBALL_DATA_TOKEN=SEU_TOKEN_FOOTBALL_DATA_AQUI
APP_ENV=development  # ou production
DOWNLOADS_FOLDER=c:\Users\SeuUsuario\Downloads
```

## 🧪 Testes

```bash
# Rodar todos os testes
pytest

# Rodar com verbose
pytest -v

# Rodar testes específicos
pytest tests/test_utils.py
pytest tests/test_pontuacao.py
pytest tests/test_auth.py

# Rodar com coverage
pytest --cov=. --cov-report=html
```

### Testes Implementados

- **test_utils.py**: Testes de validação (email, senha, nome, arquivos)
- **test_pontuacao.py**: Testes do sistema de pontuação e cálculo de pontos
- **test_auth.py**: Testes de autenticação (cadastro, login, logout)

## 🏗️ Estrutura do Projeto

```
bolao2/
├── app.py                  # Factory da aplicação Flask
├── config.py               # Configurações (dev, prod, test)
├── database.py             # Inicialização do SQLAlchemy
├── models.py               # Modelos do banco de dados
├── utils.py                # Funções utilitárias compartilhadas
├── requirements.txt        # Dependências
├── routes/                 # Rotas da aplicação
│   ├── auth.py            # Autenticação
│   ├── admin.py           # Painel administrativo
│   └── participante.py   # Área do participante
├── services/               # Serviços de negócio
│   ├── pontuacao.py       # Cálculo de pontos
│   ├── sync.py            # Sincronização API
│   ├── importador_jogos.py
│   └── importador_planilha.py
├── templates/              # Templates HTML
├── static/                 # Arquivos estáticos
└── tests/                  # Testes
    ├── conftest.py        # Fixtures do pytest
    ├── test_utils.py
    ├── test_pontuacao.py
    └── test_auth.py
```

## 🔐 Geração de SECRET_KEY

Para produção, gere uma chave segura:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copie o resultado e use como `SECRET_KEY` no `.env`.

## 📝 Notas Importantes

- A implantação gratuita usa **PostgreSQL no Neon**, independente do Render.
- SQLite permanece no desenvolvimento. Migre com `migrations.sqlite_para_postgres` conforme `DEPLOY.md`.
- Configure `DATABASE_URL` apropriadamente
- Use `APP_ENV=production` em produção
- Configure `DOWNLOADS_FOLDER` se usar importação de planilhas locais

## 🚀 Execução

```bash
# Desenvolvimento
python app.py

# Produção com gunicorn
python -m services.servidor
```

## 📄 Licença

Projeto privado.
# Tabela do campeonato

A aba `/tabela` consulta a classificação oficial da football-data.org. Configure
`FOOTBALL_DATA_TOKEN` e o código da competição em **Admin → Editar Campeonato**.
O ano corresponde ao início da temporada (ex.: 2025 para 2025/26).

Os dados ficam no banco por 15 minutos, separados por campeonato e validados
por código e temporada. Se a API falhar, o último cache compatível aparece com
aviso. Copas também consultam `/v4/competitions/{codigo}/matches` para mostrar
os confrontos de mata-mata, sem filtros de data. A disponibilidade depende
da cobertura e das permissões do token.

As zonas de cor são configuradas em `config_zonas.py`: cada zona define
`faixa`, `nome`, classes de cores e, opcionalmente, `estagios` (como
`GROUP_STAGE` ou `LEAGUE_STAGE`). As zonas da fase de liga da Champions não
são aplicadas aos grupos de temporadas anteriores.

## Correções de robustez (12/10/2026)

- `APP_ENV` seleciona `development`, `production` ou `testing`. `FLASK_ENV` ainda
  é aceito como compatibilidade, com menor prioridade. Sem seletor explícito,
  `FLASK_DEBUG=1` seleciona desenvolvimento; caso contrário, produção. Em
  produção o debugger permanece desligado, mesmo com `FLASK_DEBUG=1`.
- `RATELIMIT_STORAGE_URI` configura o Flask-Limiter; `RATELIMIT_STORAGE_URL`
  antigo e `REDIS_URL` são aceitos como fallback. `memory://` serve ao
  desenvolvimento e também o Render gratuito com `RATELIMIT_SINGLE_PROCESS=true`
  e exatamente um worker. Instale `requirements-production.txt` para psycopg e
  Gunicorn. Redis não é necessário; consulte [DEPLOY_REDIS.md](DEPLOY_REDIS.md).
- A recuperação pública de senha está desativada. A página orienta a procurar
  o administrador. Não há envio automático de e-mail ou senha padrão.
- Importação de planilhas aceita `.xlsx`, lê uploads diretamente e restringe
  a seleção local à pasta `DOWNLOADS_FOLDER` (padrão: Downloads do usuário).
  Uma falha reverte a transação e mostra uma mensagem sem detalhes internos.
- Dependências diretas Python foram fixadas nas versões do ambiente validado.
  As migrações existentes continuam específicas de SQLite.

### Importadores por linha de comando

Os dois nomes antigos usam o mesmo serviço, sem excluir registros. Cada execução
cria um novo campeonato/bolão e recusa um nome/temporada já existente. Para
atualizar um campeonato existente, use a interface. Novas identidades importadas
não recebem senha conhecida nem conta ativa.

```bash
python importar_planilha_exata.py "planilha.xlsx" --admin-email "admin@exemplo.com" --campeonato "Brasileirão" --ano 2026
python reset_e_importar_oficial.py "planilha.xlsx" --admin-email "admin@exemplo.com" --campeonato "Outro campeonato" --ano 2026
```

O administrador deve ser global e ativo. O primeiro comando inclui bônus da aba
`TOTAL`; o segundo importa jogos, resultados e palpites. O nome histórico
`reset_e_importar_oficial.py` foi mantido por compatibilidade, mas não executa reset.
