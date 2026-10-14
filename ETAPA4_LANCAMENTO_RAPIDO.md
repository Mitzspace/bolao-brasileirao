# Etapa 4 — Formulário compacto

O endpoint `admin.gerenciar_palpites` e os campos `participante_id`, `rodada_id`,
`casa_<id>`, `fora_<id>` e `primeiro_<id>` foram preservados.

A tela mostra todos os jogos em linhas adaptadas ao celular, com nomes dos times,
placares preenchidos e destaque textual para os palpites existentes. Um dígito
avança o foco; Backspace em campo vazio retorna; Tab mantém o comportamento normal;
Enter envia o lote. Para dois ou mais dígitos, desative Avanço automático e use Tab.
O campo de primeiro gol fica recolhido e mantém seu valor quando oculto.

O novo campo opcional `recebido_em` interpreta a mensagem no horário de São Paulo
e armazena UTC, como os demais horários de auditoria. Em branco, mantém o valor
existente. O recebimento é aplicado aos jogos preenchidos do lote.

Conforme a decisão posterior do usuário, jogos iniciados continuam editáveis pelo
responsável; a condição aparece na tela e os lançamentos continuam auditados.
Palpites guardados após desistência são bloqueados individualmente, sem impedir
os demais jogos. A restauração continua exigindo confirmação no histórico.

`services/lancamento_lote.py` valida todos os jogos antes de modificar objetos.
Erro retorna HTTP 422 com mensagens por jogo e os valores enviados. Nenhum item
do lote é salvo enquanto houver erro. Campos vazios não removem registros.
As gravações continuam usando os eventos existentes de PalpiteLog.

Validação: 253 testes passaram, build de CSS concluído, navegação no navegador
conferida (avanço, Backspace, Tab, dois dígitos e primeiro gol). Interface verificada
em 390px, sem transbordamento horizontal, e desktop. Renderização com cópia dos
dados atuais validada sem alterar o banco real ou a cópia. Sem migração.

Salvar e próximo e lembrar rodada ficam para a Etapa 5, mediante aprovação.
