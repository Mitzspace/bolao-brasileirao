# Etapa 1 — layout Bolt, autenticação e seleção de bolão

## Resultado

A nova interface está em `/interface/`, no mesmo servidor Flask e domínio do sistema atual.
Usa React, TypeScript, Tailwind e os componentes de navegação do Bolt. O login valida a senha
e cria a sessão existente do Flask; a escolha do bolão valida o vínculo ativo de responsável.
Não há alteração de schema, migração de dados, Supabase, cadastro público ou funcionalidade financeira.

A interface recebeu cores, fonte Inter, sidebar desktop, menu inferior mobile, cards,
transições e modo claro/escuro. A seleção utiliza nomes e IDs reais. Tema é a única informação
armazenada no localStorage; autenticação e bolão selecionado permanecem na sessão do servidor.

Esta etapa entrega a base. Campeonatos, Rodadas, Participantes e gestão de responsáveis
oferecem links para as telas atuais com o bolão correto. O Dashboard apresenta acessos operacionais;
os indicadores, Top 5 e jogos serão integrados na etapa do Dashboard. A criação de bolão ainda
abre o fluxo atual. O link “Abrir nova interface” permite retornar à interface React.

## Arquivos completos desta entrega

Todos os caminhos abaixo são relativos à raiz `bolao2`. Os arquivos estão completos no projeto
e no pacote `entregas/etapa1-visual-bolt.zip`, que mantém os mesmos caminhos.

Arquivos existentes alterados:

- `app.py`: registro do blueprint da interface.
- `routes/auth.py`: retorno à interface após login/erro/logout quando solicitado por ela.
- `templates/base.html`: link de acesso à nova interface.
- `Dockerfile`: compilação do React na etapa Node e cópia dos assets para a imagem Flask.
- `.dockerignore`: exclusão de dependências locais e arquivos de teste/entrega.
- `.gitignore`: exclusão de temporários de teste e pacote de entrega.

Arquivos novos:

- `routes/interface.py`: página, dados autorizados e seleção com CSRF.
- `templates/interface.html`: entrada React e dados serializados com escape pelo Jinja.
- `frontend/package.json` e `frontend/package-lock.json`: dependências e scripts.
- `frontend/vite.config.ts`: build dos assets em `static/interface`.
- `frontend/tsconfig.app.json`: TypeScript estrito e aliases.
- `frontend/tailwind.config.js` e `frontend/postcss.config.js`: estilos do Bolt.
- `frontend/src/main.tsx`: montagem React.
- `frontend/src/index.css`: estilos compartilhados e ajustes mobile.
- `frontend/src/types.ts`: tipos de usuário, bolão e dados iniciais.
- `frontend/src/context/AppContext.tsx`: navegação e tema.
- `frontend/src/App.tsx`: composição das telas e acessos às funcionalidades atuais.
- `frontend/src/components/layout/Sidebar.tsx`.
- `frontend/src/components/layout/BottomNav.tsx`.
- `frontend/src/components/layout/Header.tsx`.
- `frontend/src/components/layout/BolaoSelector.tsx`.
- `frontend/src/screens/LoginScreen.tsx`.
- `frontend/src/screens/BoloesScreen.tsx`.
- `tests/test_interface.py`: integração de acesso, login, seleção, revogação e CSRF.
- `ETAPA1_VISUAL_BOLT.md`: este guia.
- `static/interface/.vite/manifest.json` e arquivos de `static/interface/assets/`: build pronto.

## Compilar localmente

Na raiz do sistema, abra PowerShell e execute:

```powershell
Set-Location frontend
npm ci
npm run build
Set-Location ..
```

O `npm run build` verifica TypeScript e compila o React. Não é necessário manter Vite rodando.
Inicie o Flask como você já faz para o ambiente local e abra `/interface/` no endereço do sistema.
Os assets compilados também estão no pacote, permitindo testar sem uma primeira compilação.

## Render Free e Neon

O Dockerfile existente passa a compilar os dois conjuntos de assets: CSS/Alpine das telas atuais
e React da nova interface. O mesmo processo Python serve ambos. Não há outro serviço para publicar,
nem alteração de `DATABASE_URL`. Neon é PostgreSQL; SQLite continua suportado para uso local.

Esta entrega não foi publicada no Render. Quando você decidir testar na produção,
publique o projeto com estes arquivos e o lockfile do frontend. Após o deploy, acesse
`https://SEU-SERVICO.onrender.com/interface/` ou “Abrir nova interface” no sistema atual.

## Roteiro de teste manual

1. Abra `/interface/` sem login e confirme o visual do formulário.
2. Tente uma senha errada: deve voltar ao novo login e mostrar o erro.
3. Entre com uma conta responsável existente.
4. Com vários bolões, selecione um e confirme nome/chave no cabeçalho.
5. Troque o bolão e abra “Lançar palpites”: a tela atual deve estar no bolão escolhido.
6. Use voltar/avançar do navegador nas abas; recarregue e confirme a sessão.
7. No celular, teste menu inferior, acesso ao Dashboard pelo ícone do cabeçalho,
   seleção e saída em Configurações.
8. Troque o tema, recarregue e confirme a preferência.
9. Confira que palpites, resultados e classificação continuam operando nas telas atuais.

## Testes automatizados

```powershell
.venv\Scripts\python.exe -m pytest tests/test_interface.py tests/test_auth.py tests/test_acesso_gestao.py tests/test_escolha_bolao.py tests/test_seletor_bolao.py tests/test_deploy.py -q
```

Validação desta entrega: 66 testes passaram; TypeScript e build de produção passaram.
Os testes e a prévia visual usam banco de teste em memória, sem acessar o Neon.

## Próxima etapa

Migrar Campeonatos e tabela oficial para os componentes React, mantendo os campos,
permissões e operações existentes. As outras telas continuam disponíveis enquanto isso.
