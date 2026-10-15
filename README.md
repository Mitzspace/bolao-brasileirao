# Bolão v2

Gestão de bolões de futebol: Flask (API JSON) + interface React/TypeScript/Tailwind em
`frontend/`, servida em `/interface/`. Só responsáveis entram; eles lançam os palpites
dos participantes. Jogos, horários e resultados podem vir da API football-data.org.

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
- Token CSRF no login e no cabeçalho X-CSRFToken de toda gravação da API

### 3. Rate Limiting
- Visitantes sem login: 1000 requisições/hora por IP; responsáveis logados sem limite geral
- API da interface: 6000/hora por IP (só contra laços acidentais)
- Login: 10 por hora; troca de e-mail ou senha: 10 por hora

### 4. Validação de Inputs
- Validação de email com regex
- Validação de senha (mínimo 6 caracteres)
- Validação de nome (mínimo 2 caracteres)
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
- **test_auth.py**: Login, logout e endereços antigos
- **test_api_*.py**: Cada aba da interface (dashboard, jogos, palpites, rodadas, participantes, bolões, configurações)

## 🏗️ Estrutura do Projeto

```
bolao2/
├── app.py                  # Factory da aplicação Flask
├── config.py, models.py, utils.py, extensions.py
├── routes/
│   ├── auth.py            # Login e logout
│   ├── interface.py       # Página da interface React (/interface/)
│   └── api*.py            # API JSON de cada aba (/interface/api/...)
├── services/               # Regras de negócio (pontuação, ranking, palpites, sync...)
├── migrations/             # Migrações (SQLite: python -m migrations.X; Neon: migrations/sql)
├── frontend/               # Interface React + TS + Tailwind (npm ci && npm run build)
├── static/interface/       # Interface compilada (gerada pelo build)
├── static/escudos/         # Escudos locais dos clubes
├── templates/              # interface.html e erro.html
└── tests/
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

## 🚀 Execução

```bash
# Desenvolvimento (abra http://127.0.0.1:5000/)
python app.py
# Interface: depois de mudar algo em frontend/
cd frontend && npm ci && npm run build

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
