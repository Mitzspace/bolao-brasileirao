# Etapa 5 — Próximo participante e rodada lembrada

O formulário oferece Salvar e ficar e Salvar e próximo participante. Enter mantém
Salvar e ficar. O próximo é escolhido na ordem de nomes e ID, com retorno ao
início da lista, considerando apenas pessoas elegíveis naquela rodada que ainda
têm pendências. Conclusão de todos e pendência somente da pessoa atual recebem
mensagens distintas. Erros mantêm os valores e a pessoa selecionada.

Há setas para participantes e rodadas. Ao mudar de rodada pelas setas, a seleção
de pessoa é limpa para permitir escolher entre os elegíveis da nova rodada.
Os links e seletores usam os mesmos endpoints, com rodada e participante na URL.
Pendências ficam disponíveis no topo do lançamento e por um atalho em Meus bolões.
Cada pessoa da lista abre diretamente seu formulário naquela rodada.

A última rodada válida é lembrada na sessão assinada do navegador, separada por
usuário e bolão, para até 30 combinações recentes. Sem preferência válida, usa a
rodada atual pela regra existente. Essa preferência não é sincronizada entre
navegadores e pode ser perdida ao limpar cookies. Não houve migração do banco.

O campo opcional novo `acao` aceita `ficar` (padrão para formulários antigos) e
`proximo`. Campos e endpoints existentes foram preservados. A fórmula de pontos,
auditoria e permissão para lançamentos tardios não foram alteradas.

Validação: 257 testes passaram, incluindo saltos de participantes completos ou
desistentes, retorno ao início, conclusão, erros sem avanço, entrada tardia,
links de pendências e isolamento da memória entre usuários e bolões. CSS compilado;
layout conferido em 390px e desktop. Renderização com cópia dos dados atuais
validada; banco real e cópia permaneceram inalterados.
