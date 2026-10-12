# Etapa 2 — tela de participantes

Branch: `codex/participantes-lancamento-rapido`.

## Entrega

- Tela por bolão com nome, status em texto, rodada de entrada/desistência,
  pontos totais, quantidade de palpites e observação.
- Filtros Todos, Ativos e Desistentes, com contagens. Padrão Todos; ordenação
  por ativos, desistentes, saiu (legado) e removidos; nome e ID desempatarão.
- Edição de nome/observação com histórico transacional e preservação do texto
  quando o nome é inválido. Conteúdo livre é escapado no HTML.
- Inclusão sem conta de acesso; rodada de entrada obrigatória, validada no
  campeonato do bolão. Sugestão: rodada de referência atual; sem jogos, primeira
  rodada cadastrada. Sem rodadas, orientar cadastro antes de incluir a pessoa.
- Nomes repetidos são detectados por acento, caixa e espaços. O aviso não bloqueia
  inclusão/edição; a lista sinaliza homônimos e mostra seus números de registro.
- Não há exclusão de participante. A ação preexistente Remover do bolão continua
  alterando apenas status, com as proteções de responsável e histórico existentes.

## Compatibilidade e limites desta etapa

Endpoints e campos existentes não foram renomeados. Campos acrescentados:
`observacao`, `rodada_entrada_id` (obrigatório na inclusão), e `filtro`.
Clientes antigos que enviam inclusão sem rodada recebem HTTP 422 com formulário
preenchido e orientação. Na edição, omitir `observacao` preserva o valor anterior;
enviar vazio limpa a observação, mantendo o histórico.

A listagem calcula os mesmos pontos do ranking atual, usando `calcular_pontuacao`
e somando créditos históricos. Não altera a fórmula nem os dados.
As rodadas de entrada estão registradas, mas a integração de elegibilidade com
ranking, pendências e lançamento será feita na Etapa 3, conforme o plano aprovado.
Registrar/corrigir/reverter desistência também pertence à Etapa 3.
Nenhuma migração foi necessária nesta etapa.

## Verificação

- 237 testes passaram, incluindo 13 novos casos de inclusão/edição, rodada
  obrigatória e de outro campeonato, homônimos, escape de HTML, filtros,
  totais com créditos históricos e autorização.
- CSS recompilado com `npm run build:css`.
- Na cópia dos dados atuais, pontos individuais conferidos com o ranking;
  24 participações e 5.652 palpites preservados. Filtros responderam HTTP 200.
  Hashes de schema/dados confirmaram que banco real e cópia não foram alterados.
- Revisão visual no navegador: celular com iframe de 390 px (área útil 375 px,
  sem transbordamento horizontal) e desktop. Inclusão e edição legíveis.
- Prévia celular: `instance/participantes-etapa2-mobile.png`.
- Prévia desktop: `instance/participantes-etapa2-desktop.png`.
