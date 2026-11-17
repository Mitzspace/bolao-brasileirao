# Produção na Oracle Cloud

Guia da hospedagem atual (desde nov/2026). Substitui a implantação Render + Neon
descrita em [DEPLOY.md](DEPLOY.md), que fica só como histórico.

Endereço IP, subdomínio, senhas e tokens **não** ficam neste repositório: eles
estão no `.env` do servidor, no `~/.pgpass` e nas anotações pessoais do responsável.

## 1. Visão geral

| Peça | Como está |
| --- | --- |
| Máquina | VM Always Free `VM.Standard.E2.1.Micro` (AMD, 1/8 OCPU, **1 GB de RAM** + 2 GB de swap em `/swapfile`), região São Paulo |
| Sistema | Ubuntu 24.04 **Minimal**, usuário `ubuntu`, fuso `America/Sao_Paulo` |
| Aplicação | `~/bolao-brasileirao` (branch `main`), venv em `.venv`, serviço systemd `bolao` |
| Banco | PostgreSQL 18 (repositório PGDG) na própria VM: banco `bolao`, usuário `bolao` |
| HTTPS | Caddy (`/etc/caddy/Caddyfile`) com certificado automático para um subdomínio DuckDNS, repassando para `127.0.0.1:8000` |
| Interface | Node 22 (NodeSource) só para compilar o bundle do Vite |
| Rede | Portas 80/443 liberadas na Security List da Oracle **e** no iptables (`netfilter-persistent`) |

O Ubuntu Minimal vem sem `nano`, `cron` e `tmux`; eles foram instalados à parte.

## 2. Acesso

- Do notebook: `ssh swill` (atalho no `~/.ssh/config`, com `ServerAliveInterval 60`).
- Em redes que bloqueiam a porta 22 (ex.: faculdade), use o **Cloud Shell** da Oracle
  no navegador. Ele tem a chave e o mesmo atalho `ssh swill`.

## 3. Serviço `bolao`

`/etc/systemd/system/bolao.service` roda `python -m services.servidor` (gunicorn +
sincronização opcional) a partir de `~/bolao-brasileirao`, com
`EnvironmentFile=~/bolao-brasileirao/.env`, ouvindo na porta 8000.

```bash
sudo systemctl status bolao
```

```bash
sudo journalctl -u bolao -n 50
```

```bash
sudo systemctl restart bolao
```

Qualquer mudança no `.env` só vale depois do `restart`.

### Variáveis do `.env` (nomes; valores só no servidor)

| Variável | Valor / observação |
| --- | --- |
| `APP_ENV` | `production` |
| `SECRET_KEY` | chave longa e estável (trocar derruba as sessões) |
| `DATABASE_URL` | `postgresql://bolao:SENHA@localhost:5432/bolao?sslmode=require`. Em produção o app **recusa** conexão sem TLS (`normalizar_database_url` em `config.py`), por isso o `sslmode=require` mesmo com o banco local |
| `TRUST_PROXY` | `true` (o Caddy é o único proxy na frente) |
| `RATELIMIT_STORAGE_URI` | `memory://` |
| `RATELIMIT_SINGLE_PROCESS` | `true` (sem isso o app não aceita limiter em memória) |
| `TRUSTED_HOSTS` | o subdomínio DuckDNS, sem `https://` |
| `SYNC_ENABLED` | `true` (sincronização periódica com a football-data.org) |
| `FOOTBALL_DATA_TOKEN` | token da football-data.org |
| `PORT` | `8000` |

## 4. Atualizar depois de um merge na `main`

A VM tem só 1 GB de RAM: **pare o serviço antes do build** da interface, senão o
`npm` pode ficar sem memória.

```bash
cd ~/bolao-brasileirao && git pull
```

```bash
.venv/bin/pip install -r requirements-production.txt
```

```bash
sudo systemctl stop bolao
```

```bash
cd ~/bolao-brasileirao/frontend && npm ci && npm run build
```

```bash
sudo systemctl start bolao
```

Depois confira `sudo journalctl -u bolao -n 50` e abra o site.

Se o PR trouxer migração de banco, o app não sobe e o log aponta qual falta. Faça
um backup (seção 5) e rode o SQL de `migrations/sql/` correspondente com `psql`
antes do `start`.

## 5. Backups

- `~/backup-bolao.sh` faz `pg_dump -Fc` em `~/backups/bolao-AAAA-MM-DD.dump` e apaga
  os arquivos com mais de 14 dias.
- Roda pelo cron todo dia às 3h30; o log fica em `~/backups/cron.log`.
- Cópia para o notebook:

```bash
rsync -av swill:~/backups/ ~/backups-bolao/
```

  **Pendente:** em nov/2026 essa cópia ainda não estava chegando ao notebook. Conferir.

Restaurar (num banco de teste primeiro):

```bash
createdb -U bolao bolao_teste && pg_restore -U bolao -d bolao_teste ~/backups/bolao-AAAA-MM-DD.dump
```

## 6. Capacidade

Teste de carga feito no próprio servidor: teto de ~38 requisições/s (~10 pessoas
abrindo o link público por segundo), sem erros até 200 conexões simultâneas. O
gargalo é a CPU (1/8 OCPU), não a memória nem o banco.

## 7. Saída do Render e do Neon

- Dados copiados do Neon em 02/11/2026. Como o Render ainda recebeu uso depois disso,
  em 05/11 o Neon foi restaurado num banco à parte (`bolao_neon`) e comparado com
  `scripts/juntar_neon.py` (branch `ferramenta-juntar-neon`): não havia nada a trazer.
- Backup final do Neon: `~/backups/neon-2026-11-05.dump` no servidor.
- Pendências:
  - confirmar que o banco `bolao_neon` foi apagado da VM;
  - manter o serviço do Render suspenso;
  - depois de algumas semanas sem problemas, apagar o serviço do Render e o projeto do Neon.
