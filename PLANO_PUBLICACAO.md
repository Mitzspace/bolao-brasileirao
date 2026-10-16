# Plano de publicação: gestão hoje, consulta pelos participantes amanhã

> Plano apenas — nada disto está implementado. Etapas curtas, em ordem de prioridade.
> Limites conferidos em out/2026 nas páginas do Render e do Neon (ver Fontes).

## Onde estamos
- **Uma aplicação** (Flask + React) no Render Free, banco no Neon Free (mesma região, Ohio).
- **Só responsáveis entram** (login + senha). Toda rota que grava exige login de
  responsável do bolão (`requer_gestao`), tem proteção CSRF e o login tem limite de tentativas.
- Cookies seguros, HSTS e `SECRET_KEY` obrigatória em produção já estão configurados.

## Arquitetura recomendada para a consulta: link secreto por bolão, sem login
A forma mais simples que atende "só visualizar":

```
Responsável (login)  ──►  /interface/...        (como hoje: lê e grava)
Participante (link)  ──►  /c/<código-do-link>  (só leitura, sem login)
                               │
                     mesmo app, mesmo banco, mesmas regras de cálculo
```

- **Link**: cada bolão ganha um código aleatório longo (ex.: 32 caracteres), gravado numa
  coluna nova `bolao.codigo_consulta`. Vazio = link desligado. O responsável
  **gera, copia e revoga** o link na tela de Bolões (revogar = gerar outro; o antigo para na hora).
- **Rotas públicas só de leitura** num módulo separado (`routes/publico.py`): somente `GET`,
  sem sessão, sem CSRF, sem nenhum caminho até as rotas de gravação.
- **O que o participante vê**: classificação geral e por rodada, jogos/resultados e a grade de
  palpites — **palpites só de jogos já iniciados** (para ninguém copiar o palpite dos outros).
- **O que nunca aparece**: e-mails, observações, histórico de alterações, palpites "guardados"
  de desistentes, botões de gestão.
- **Interface**: uma página React própria e enxuta (entrada separada no Vite), reaproveitando
  os componentes visuais (pódio, tabela, cards). O código de gestão não é enviado ao navegador
  do participante.
- **Por que sem login**: zero cadastro e zero senha para recuperar. O risco é o link vazar,
  mas ele só mostra o que já seria compartilhado no grupo do WhatsApp e pode ser revogado.
- **Alternativa descartada**: código curto (ex.: 6 dígitos) é fácil de adivinhar por tentativa;
  exigiria login ou bloqueios agressivos. O link longo resolve sem atrito.

## Limitações do plano gratuito e como contornar
| Limite | Impacto na consulta pública | Mitigação |
|---|---|---|
| Render dorme após **15 min** sem acesso e leva **~1 min** para acordar | Participante abre o link e espera | Keep-alive em horário de uso (ver `DESEMPENHO.md`); a página mostra "carregando" |
| Render: **750 h/mês** por conta, contando todos os serviços grátis | Keep-alive 24 h consome ~744 h | Keep-alive só 8h–23h (~500 h) |
| Render: banda e minutos de build com cota mensal; se estourar sem cartão, o serviço é suspenso até o mês seguinte | Muitos acessos poderiam pesar | Respostas comprimidas e em cache: 1º acesso ~110 KB, depois ~10 KB por visita |
| Render: CPU pequena e reinícios a qualquer momento | Classificação é o cálculo mais pesado | Cache em memória das respostas públicas, limpo a cada gravação (Etapa 3) |
| Neon: **100 CU-horas/mês**, suspende após **5 min** parado, **1 GB** por projeto, **5 GB/mês** de transferência | Cada acesso público acorda o banco | Cache das respostas públicas; keep-alive no `/healthz` (não usa banco) |
| Neon: restauração só das **últimas 6 h** + **1** snapshot manual | Um erro descoberto depois de um dia não volta pelo Neon | Backup semanal próprio (Etapa 1) |
| **Postgres grátis do Render expira em 30 dias** | — | Continuar no Neon (não expira) |

## Etapas (prioridade e custo)

**Etapa 1 — Segurança e backup (agora, R$ 0, ~1 h)**
1. Conferir no Render que `SECRET_KEY` foi gerada pelo Render e que a `DATABASE_URL` só está nas
   variáveis de ambiente. (Conferido: `.env*` e `instance/` já estão no `.gitignore` e no
   `.dockerignore`, então senhas e bancos locais não vão para o GitHub nem para a imagem.)
2. Rodar `git log --all -- .env .env.neon.local` uma vez: se aparecer algum commit antigo com esses
   arquivos, trocar a senha do banco no Neon e o token da football-data.
3. Backup semanal do Neon com `pg_dump` (o projeto já tem o PostgreSQL portátil em
   `instance/pg-portable`): um agendamento do Windows que salva
   `bolao-AAAA-MM-DD.dump` numa pasta sincronizada (OneDrive/Google Drive), guardando as 8 últimas.
4. Antes de cada migração SQL: snapshot/branch no Neon (já é o procedimento dos `MIGRACAO*.md`).

**Etapa 2 — Link de consulta, versão mínima (R$ 0, ~1–2 dias)**
1. Migração: `bolao.codigo_consulta` (texto único, opcional) + SQL para o Neon.
2. `routes/publico.py`: `GET /c/<codigo>` (página) e `GET /c/<codigo>/api/classificacao`,
   `/rodadas/<id>`, `/jogos` — reaproveitando `services/ranking.py`, `grade_palpites.py` etc.
3. Serializadores públicos (sem dados pessoais) e regra "palpites só de jogos iniciados".
4. Tela de Bolões: "Gerar link de consulta", "Copiar", "Revogar".
5. Proteções: limite por IP nas rotas públicas, cabeçalho `X-Robots-Tag: noindex`, código
   comparado em tempo constante, respostas com cache curto (60 s).
6. Testes: link inválido/revogado = 404; nenhuma rota pública grava; palpite de jogo
   não iniciado não aparece; nenhum e-mail no JSON.

**Etapa 3 — Robustez para vários acessos (R$ 0, ~meio dia)**
1. Cache em memória das respostas públicas por bolão, limpo automaticamente a cada gravação
   (o app roda com um único processo, então o cache é consistente).
2. Página pública "leve": só a classificação no primeiro carregamento; grade e jogos sob demanda.

**Etapa 4 — Quando "grátis" deixar de bastar (decisão sua)**
| Opção | Custo | O que muda |
|---|---|---|
| Continuar no Render Free + keep-alive | R$ 0 | Bom para uso de grupo; ~1 min de espera fora do horário do keep-alive |
| **Google Cloud Run** (camada gratuita mensal: 2 milhões de requisições, 180 mil vCPU-segundos) | R$ 0 na prática; exige conta de faturamento (cartão) | Acorda em segundos, não em 1 min; o projeto já tem Dockerfile, então a mudança é pequena |
| Koyeb Free (1 serviço, 512 MB, 0,1 vCPU, Frankfurt ou Washington) | R$ 0; exige cartão | Parecido com o Render; não resolve muito |
| Oracle Always Free (VM ARM, hoje 2 OCPU/12 GB) | R$ 0; exige cartão e manutenção de servidor | Sempre ligado, mas você cuida de Linux, HTTPS e atualizações |
| **Render pago** (instância de US$ 7/mês, 512 MB) | ~US$ 7/mês | A opção mais simples para nunca dormir: mesmo deploy de hoje |
| Neon pago | conforme uso | Só se passar de 100 CU-h/mês ou precisar de restauração mais longa |

Recomendação: Etapas 1→2→3 no plano gratuito. Se o grupo reclamar da espera, primeiro amplie
o horário do keep-alive; se ainda assim incomodar, o Render pago é a troca com menos trabalho.

## Fontes
- Render — Deploy for Free: https://render.com/docs/free
- Render — Pricing: https://render.com/pricing
- Neon — Free plan limits: https://neon.com/faqs/free-plan-limits-and-quotas
- Koyeb — Pricing FAQ: https://www.koyeb.com/docs/faqs/pricing
- Cloud Run (camada gratuita; confirme no console do Google): https://agentdeals.dev/vendor/google-cloud-run
- Oracle Always Free (redução de 2026): https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/
