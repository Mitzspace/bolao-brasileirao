Revisão visual — 4 de outubro de 2026
====================================

As 26 telas existentes compartilham o tema verde escuro inspirado no Lovable.
Cards, formulários, tabelas, estados, botões e navegação administrativa usam os
componentes de `static/css/ui.source.css`. O CSS anterior e a adaptação provisória
foram removidos. Tailwind e Alpine são servidos localmente; as fontes têm fallback
sans-serif caso o Google Fonts não esteja disponível.

Para recompilar os assets após alterar classes ou componentes:

    npm ci
    npm run build:css

`static/css/ui.css` e `static/js/alpine.min.js` são distribuídos com o aplicativo;
Node não é necessário para executar o Flask. O lockfile fixa as dependências.

Verificação realizada:

- Renderização das 26 telas, incluindo todas as páginas administrativas,
  autenticação, erros 403/429, rodada, grade, ranking e classificação.
- Inspeção visual no navegador em desktop e verificação de largura em celular
  (390 px), com tabelas largas contidas em áreas de rolagem horizontal.
- Menu móvel abre e fecha com Alpine servido localmente.
- 83 testes passaram. As verificações usaram cópias do banco real; o arquivo
  original permaneceu idêntico por SHA-256.

Nesta revisão não foram alterados rotas, nomes dos campos dos formulários,
sincronização, cálculo de pontos ou regras de autorização. Não foi iniciada a
Fase 2. A classificação da prévia foi consultada do cache, sem chamada à API.
