# Etapa 3 — Desistência e elegibilidade

Implementada na branch `codex/participantes-lancamento-rapido`.

A rodada informada é a primeira sem participação. A regra está centralizada em
`services/elegibilidade.py`. Entrada tardia respeita a política do bolão; rodadas
anteriores nunca geram pendências ou permitem novos lançamentos.

Em Participantes, use Registrar desistência, Editar desistência ou Reativar.
A rota `/b/<bolao>/participacoes/<id>/desistencia` exige responsável pelo bolão.
Toda operação passa por prévia e confirmação vinculada ao usuário e ao estado
dos dados. Uma prévia desatualizada exige nova revisão.

Palpites posteriores são preservados e marcados como após desistência. A correção
da rodada ou reativação exige escolha explícita para recuperar palpites elegíveis.
Também é possível mantê-los guardados e restaurar depois pela tela de histórico.
As marcações e restaurações são registradas em PalpiteLog; alterações de nome,
status, rodada e motivo ficam em ParticipacaoLog. Reativar não devolve acesso
administrativo automaticamente. O último responsável não pode desistir sem que
outro responsável assuma.

Ranking geral mantém o desistente e os pontos anteriores; o filtro de ocultação
é apenas visual. Ranking por rodada, grade, lançamento e pendências respeitam
o período. Créditos históricos seguem esse período, sem exclusão física.
A fórmula de pontos não foi alterada; os valores continuam derivados do
resultado oficial. Não há bloqueio por horário para o responsável.

Enquanto houver palpites guardados numa rodada, o formulário antigo orienta
a revisão da restauração antes de aceitar novos lançamentos nessa rodada.
O formulário compacto será tratado na Etapa 4.

Não houve migração nesta etapa nem mudança de endpoints ou nomes dos campos
dos formulários existentes. O backup da migração da Etapa 1 continua preservado.

Validação: 244 testes passaram, incluindo prévia sem escrita, preservação dos
valores originais, rankings anteriores e posteriores, correção, reativação com
e sem restauração, token inválido, prévia desatualizada, autorização e proteção
de importação. Build de CSS concluído. Avisos existentes de depreciação permanecem.
Numa cópia do banco atual, foram comparados ranking geral e todas as rodadas,
simulados desistência e retorno, e preservados os 5.652 palpites. O digest do
banco original permaneceu igual. Interface conferida em 390px e desktop.
