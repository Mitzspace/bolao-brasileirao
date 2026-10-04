# Bolão v2

Sistema de bolão de futebol em Flask com sincronização automática via API football-data.org.

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
FLASK_ENV=development  # ou production
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

- **SQLite** é recomendado apenas para desenvolvimento
- Para produção, use **PostgreSQL** ou **MySQL**
- Configure `DATABASE_URL` apropriadamente
- Use `FLASK_ENV=production` em produção
- Configure `DOWNLOADS_FOLDER` se usar importação de planilhas locais

## 🚀 Execução

```bash
# Desenvolvimento
python app.py

# Produção com gunicorn
gunicorn wsgi:app
```

## 📄 Licença

Projeto privado.
