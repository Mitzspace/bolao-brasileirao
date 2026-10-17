# Etapa 4 — criação de bolão e participantes sem conta

Implementada na branch `codex/gestao-admin-etapa1`, sem migração de esquema.

## Criação

O botão Criar bolão em Meus bolões abre `/boloes/novo`. A tela permite escolher
um campeonato global já cadastrado e, opcionalmente, carregar a lista de um
bolão gerenciado pelo usuário para marcar os participantes a copiar.

- A fonte é validada no servidor; registros de outra fonte são recusados.
- O administrador é incluído automaticamente como responsável no novo bolão.
  Sua participação vinculada na fonte não é oferecida como cópia duplicada.
- Cada registro marcado vira uma nova Participacao ativa, com o mesmo nome,
  papel participante e sem usuario_id ou participante_legado_id.
- Palpites, bônus, logs, contas, convites e permissões não são copiados.
- Registros inativos na fonte podem ser escolhidos; o status aparece na lista.
  A cópia nasce ativa sem modificar o registro original.
- IDs repetidos no formulário são deduplicados; nomes iguais continuam sendo
  pessoas independentes, identificadas por ID. Não houve criação de entidade Pessoa.
- A criação completa é transacional e o novo bolão fica selecionado ao terminar.
- Um administrador global sem bolão também pode criar seu primeiro bolão.
  Cadastro público de administradores continua desativado.

## Gestão local de participações

A tela Participantes oferece cadastro apenas com nome, edição do nome local,
remoção por status e reativação. Os controles usam novas rotas e campos próprios:

- `/b/<id>/participacoes/nova` — POST, `nome_exibicao`.
- `/b/<id>/participacoes/<participacao_id>/editar` — POST, `nome_exibicao`.
- `/b/<id>/participacoes/<participacao_id>/status` — POST, `acao=remover|reativar`.

Os handlers legados e nomes de campos antigos foram preservados. As novas rotas
têm aliases sob `/admin`, seguindo os redirecionamentos da Etapa 3.

Nomes são validados no servidor (2 a 100 caracteres). Edição afeta apenas o nome
da participação, sem alterar conta ou outro bolão. Remoção muda status e saiu_em,
sem apagar registros. Reativação mantém ID, datas de entrada/pontuação, palpites
e créditos; limpa saiu_em e volta ao papel participante. A concessão de acesso
de responsável ocorre separadamente em Configurações.

Todas as mutações exigem responsabilidade no bolão e CSRF. A proteção do último
responsável habilitado também vale para a remoção nesta tela.

## Validação

- 199 testes aprovados, incluindo 15 casos novos: cópia seletiva, troca de
  campeonato, duplicação de IDs, campos inválidos, autorização da fonte, CRUD,
  proteção do último responsável, preservação do histórico e CSRF.
- Em cópia do banco atual, criação com dois participantes copiados e ciclo de
  remoção/reativação. Contagens de palpites, logs, bônus e contas preservadas.
- Banco original com SHA-256 idêntico antes e depois da verificação.
- CSS recompilado com o Tailwind existente; novas telas usam base.html.

Etapa 5 depende de aprovação: texto copiável do ranking geral/rodada e resumo
da rodada para WhatsApp. Link público somente leitura requer aprovação específica.
