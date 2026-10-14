# Etapa 1 — acesso para gestão

Branch: `codex/gestao-admin-etapa1`.

`FEATURE_PARTICIPANTE_LOGIN` é falsa por padrão. O `.env` existente não foi alterado.
Nesse modo:

- `/cadastro`, `/meus-palpites` e `/rodada/<id>` retornam 404.
- O login exige administrador global ou participação ativa com papel `responsavel`.
- Sessões anteriores de contas exclusivamente participantes recebem 403; logout continua disponível.
- Bolões disponíveis para gestão exigem participação ativa como responsável.
- Links de palpite próprio passam a apontar para o lançamento administrativo.
- As rotas de consulta de ranking, jogos e grade continuam disponíveis aos responsáveis.

Para reativar o fluxo legado, configure `FEATURE_PARTICIPANTE_LOGIN=true` no ambiente
e reinicie a aplicação. Em testes, a configuração pode ser alterada diretamente em
`app.config`. Isso restaura os fluxos existentes; não implementa convites ou vinculação
que ainda não existiam nesta versão.

Não houve migração, exclusão de registros, alteração de endpoints ou nomes de campos
de formulário. Os valores de `permite_palpite_proprio` foram preservados. Pontuação,
sincronização e regras atuais de lançamento administrativo permanecem como estavam.
O cadastro público de novos administradores ainda não foi implementado.

## Validação

- Suíte completa: 157 testes aprovados, incluindo 13 casos novos de acesso/reativação.
- Os testes legados habilitam explicitamente a flag para continuar cobrindo esse fluxo.
- Em uma cópia SQLite dos dados atuais, foram verificadas as telas de gestão e a
  alteração de um palpite de participante sem conta, com um novo log de auditoria.
- Nenhuma participação ou palpite foi excluído. O SHA-256 do banco original permaneceu igual.
- A cópia de validação é um artefato de teste, não deve substituir o banco de uso.

As próximas etapas dependem de confirmação. Permanecem as lacunas identificadas na
Etapa 0: gestão legada de participantes, ausência de CSV e pendências, lançamento
administrativo após início sem bloqueio e horários de jogos locais sem fuso.
