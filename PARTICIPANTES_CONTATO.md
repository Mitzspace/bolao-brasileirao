# Edição de participantes e mesclagem do Albert

Na aba Participantes, abra **Editar participante** para alterar e-mail de contato
e **Responsável: Sim/Não**. O e-mail é opcional, validado no servidor e não muda
credenciais de login. Alterações entram no histórico da participação. O último
responsável com conta habilitada não pode perder o acesso.

Nomes normalizados (incluindo espaços, maiúsculas e acentos) e e-mails repetidos
são recusados no cadastro/edição deste bolão. Em Configurações, use **Vincular a
um participante existente** ao adicionar uma conta responsável para uma pessoa
que já tem histórico. O vínculo é explícito; nomes iguais não vinculam contas
automaticamente.

## Migração antes da publicação

- SQLite: `python -m migrations.contato_participante CAMINHO_DO_BANCO`.
  Gera backup e é idempotente.
- PostgreSQL: após backup, aplicar `migrations/sql/004_contato_participante.sql`.
- Não usar o SQLite local para substituir o banco publicado.

## Operação realizada em 13/10/2026

No banco publicado, o Albert original (#4) tinha 300 palpites e 38 bônus.
O Albert administrador (#25) tinha a conta #45 e nenhum palpite ou bônus.
A participação #4 recebeu a conta e o papel de responsável. As duas contas
legadas de usuário foram mantidas; senhas e referências a autores não mudaram.
Os cinco logs da participação #25 foram vinculados à #4 sem mudar conteúdo,
autor ou data. Um novo log de mesclagem guarda os dois registros anteriores.
O registro principal mantém a data de entrada mais antiga e o nome Albert.

Foi salvo um backup integral dos dados em `instance/backups` antes da operação.
Ele contém dados privados e não deve ser enviado ao Git. A operação usou uma
transação e verificou contagens de palpites, bônus, usuários e logs.
