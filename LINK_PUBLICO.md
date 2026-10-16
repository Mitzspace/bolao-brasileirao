# Link público de consulta (somente leitura, sem login)

## Como funciona
- Cada bolão pode ter **um link secreto**: `https://SEU-APP/publico/<código>` (22 caracteres aleatórios).
- Quem tem o link vê 4 abas: **Início** (indicadores, jogos da rodada atual e tabela),
  **Jogos**, **Palpites** e **Participantes**. Ninguém consegue alterar nada.
- O admin controla tudo em **Bolões › (bolão) › aba "Link público"**:
  - **Criar link**, **Copiar**, **Ver como participante** (abre a página pública numa aba nova);
  - **Gerar novo link**: o link antigo para de funcionar na hora;
  - **Desativar**: ninguém mais abre a página;
  - **Classificação para o público**: "Mostrar ao público até [rodada]" ou "oculta".
    O sistema sugere a última rodada com todos os resultados ("Liberar até a 30ª Rodada").

## Regras de visibilidade (aplicadas no servidor)
| Item | Regra |
|---|---|
| Palpites | Só de jogos com **resultado registrado**. "Encerrar para palpites" sem placar **não** revela. A consulta ao banco já filtra os jogos com resultado: palpites de jogos futuros nem são lidos. |
| Pontos e tabela | Só até a rodada liberada. Rodadas seguintes mostram palpites e placares, sem pontos. Sem rodada liberada, nenhum ponto é enviado e a aba mostra "A classificação será divulgada em breve". |
| Dashboard | Sem palpites faltantes/pendências. Líder e top 5 só com tabela liberada. |
| Participantes | Ativos e desistentes (desistentes ocultos por padrão, com chave para mostrar). Sem e-mail, observação ou motivo de desistência. |
| Identificação | Rodadas pelo número (1, 2, 3...), nunca pelo id do banco. Nenhum id interno no JSON. |

"Ocultar desistentes" agora vem **ligado por padrão** também na classificação do admin.

## Segurança
- Rotas públicas em módulo separado (`routes/publico.py`), **somente GET** (POST/PUT/PATCH/DELETE → 405),
  sem sessão e sem login; o admin continua exigindo login (401 para quem só tem o link).
- Código inválido, revogado ou malformado → mesmo 404 genérico (não revela se o bolão existe).
- Limite por IP: 90 acessos/minuto e 1500/hora nas rotas públicas.
- Cabeçalhos: `noindex` (não aparece no Google) e `no-referrer` (o código não vaza para outros sites).
- Só responsáveis do bolão configuram o link e a tabela.

## Desempenho (plano gratuito)
- Cache em memória das respostas públicas (60 s), **limpo automaticamente a cada gravação** no admin;
  o navegador guarda por 15 s. Dados por rodada, não tudo de uma vez.
- Página pública separada e leve (~58 KB comprimidos), sem o código do admin.
- Barra de progresso e esqueletos de carregamento; aviso de "servidor acordando" no cold start.

## Como publicar
1. Backup/branch no Neon.
2. SQL Editor do Neon (branch principal): rode `migrations/sql/009_link_publico.sql`.
   Conferência no fim do arquivo: deve listar `codigo_publico` e `rodada_publica_id`.
3. Local: `python -m migrations.link_publico instance/banco.db` (faz backup).
4. `git add -A`, `git commit`, `git push origin nova-interface` e **Deploy latest commit** no Render.

Os bolões começam com link desligado e tabela oculta: nada fica público até você criar o link.

## Testes
`python -m pytest tests/test_publico.py -v` — 19 casos: jogo futuro com palpite, jogo "encerrado" sem
placar, jogo com resultado, tabela oculta/liberada/por rodada, varredura de dados pessoais e ids,
link inválido/revogado, métodos de gravação recusados, admin inacessível pelo link, permissões,
cache após gravar resultado, limite de requisições e carregamento do CSS das duas páginas.
