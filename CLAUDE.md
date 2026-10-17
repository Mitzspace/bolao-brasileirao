# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é

Gestão de bolões de futebol (texto e UI em português). Backend Flask com API JSON + interface React/TypeScript/Tailwind (Vite) em `frontend/`, servida em `/interface/`. Só responsáveis (admins/gestores) fazem login; eles lançam os palpites dos participantes. Jogos e resultados podem ser sincronizados da API football-data.org. Há também uma área pública somente leitura por link (`routes/publico.py`, `services/publico.py`).

## Comandos

```bash
pip install -r requirements.txt            # dev; produção usa requirements-production.txt
cp .env.example .env                       # SECRET_KEY, DATABASE_URL, FOOTBALL_DATA_TOKEN, APP_ENV
python app.py                              # dev em http://127.0.0.1:5000/ (SQLite)
python -m services.servidor                # modo produção (gunicorn + sync opcional)

python -m pytest -q                        # suíte inteira (~2,5 min)
python -m pytest tests/test_pontuacao.py -k nome_do_teste   # um teste

cd frontend && npm ci && npm run build     # typecheck (tsc) + vite build -> ../static/interface
cd frontend && npm run typecheck           # só tipos
```

Não há linter configurado. O `pytest.ini` já injeta `-v --tb=short`.

`static/interface/` (bundle do Vite) **não é versionado**: rode `npm run build` antes de abrir a interface ou de rodar `tests/test_http_desempenho.py` e `tests/test_publico.py`, que dependem de `.vite/manifest.json`. O `Dockerfile` gera o bundle num estágio Node.

## Arquitetura

- **`app.py` – `create_app(config_name, ...)`**: factory. `APP_ENV` (ou `FLASK_ENV`; sem nenhum, `FLASK_DEBUG=1` → development, senão production) escolhe a classe de `config.py`. Testes usam `create_app("testing")` com SQLite em memória (`tests/conftest.py`).
- **Camadas**: `routes/` (blueprints finos; `api_*.py` por aba da interface, em `/interface/api/...`) → `services/` (toda a regra de negócio: `pontuacao`, `regras_pontuacao`, `classificacao`/`ranking`, `elegibilidade`, `lancamento_*`, `sync`, parsers de planilha/WhatsApp, `publico`) → `models.py` (SQLAlchemy; `database.py` expõe `db`). Prefira pôr lógica nova em `services/`.
- **Modelo multi-bolão**: `Campeonato` → `Rodada` → `Jogo` (+ `Resultado`); `Bolao` pertence a um campeonato e tem regras de pontuação próprias; `Participante` é a conta (login), `Participacao` liga uma pessoa a um bolão (nome de exibição, papel, status, desistência/entrada tardia); `Palpite` pertence a uma `Participacao`, com `PalpiteLog`/`ParticipacaoLog` de auditoria. Ranking e pontos dependem de elegibilidade (período de participação, desistência) — ver `services/elegibilidade.py` antes de mexer em classificação.
- **Frontend**: `frontend/src/` com `screens/` (uma por aba) e `components/`; tipos da API em `types.ts`. `routes/interface.py` + `templates/interface.html` carregam o bundle via `services/assets_vite.py`, que lê o manifesto do Vite (duas entradas: gestão e página pública).
- **Segurança/infra**: CSRF global (token no header `X-CSRFToken` nas gravações da API), Flask-Limiter (`extensions.py`; storage via `RATELIMIT_STORAGE_URI`, memória no Render Free), `TRUST_PROXY` para ProxyFix, `MAINTENANCE_MODE` sobe `services/manutencao.py`.

## Banco e migrações (ponto de atenção)

O app **não migra o banco sozinho**. Em `create_app`, para bancos já existentes ele inspeciona colunas/tabelas obrigatórias e lança `RuntimeError` apontando a migração faltante (`python -m migrations.<nome> CAMINHO_DO_BANCO`, com backup antes; detalhes em `docs/`). Em produção, banco vazio exige `python -m scripts.inicializar_banco`, e schema parcial falha o startup. Ao adicionar coluna: crie a migração em `migrations/` (SQLite), o SQL equivalente em `migrations/sql/` (Neon/Postgres) e inclua a checagem em `create_app`. Dev usa SQLite; produção usa PostgreSQL (Neon, `postgresql+psycopg`, TLS obrigatório — ver `normalizar_database_url` em `config.py`). Testes de Postgres usam `TEST_POSTGRES_URL` (rodam no workflow manual `deploy-check.yml`).

## Convenções

- Código, mensagens e comentários em português; nomes de times são normalizados na sincronização (`test_nomes_times.py`) — os testes esperam o nome curto (ex.: `Corinthians`).
- Documentação de cada etapa/feature fica em `docs/` (guias de deploy: `DEPLOY.md`, `DEPLOY_REDIS.md` na raiz). Mensagens de erro de migração referenciam esses arquivos.
- Em desenvolvimento a `SECRET_KEY` padrão é fixa (para manter sessões entre reinícios); produção exige a variável de ambiente.
