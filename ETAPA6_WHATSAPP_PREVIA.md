# Etapa 6 — Colar mensagem com prévia

Ampliação com os três exemplos reais: cabeçalho `*Rodada-30*` é reconhecido e
conferido com a rodada selecionada; divergência bloqueia a prévia. O marcador
`★` separa o jogador do primeiro gol, com ou sem espaço, preservando acentos e
nomes compostos. O jogador é editável na prévia e preenche o campo de bônus do
formulário. Se o jogo não estiver cadastrado como clássico, exige correção em
vez de descartar o jogador silenciosamente. Blocos de participantes diferentes
colados juntos continuam gerando alertas de jogos repetidos.
Os três exemplos completos estão cobertos em `tests/test_whatsapp_exemplos_reais.py`.

Escolha participante e rodada no formulário e abra Colar mensagem do WhatsApp.
Gerar prévia usa um parser local determinístico, sem chamadas externas. Reconhece
placares com x, hífen ou a, nomes normalizados sem acentos/FC/EC/SC e numeração.
Apelidos ficam no dicionário APELIDOS de `services/parser_whatsapp.py`.
Sem times, utiliza a ordem exibida dos jogos, com aviso explícito. Numeração
explícita identifica a posição correspondente na rodada.

A prévia permite corrigir jogo e gols ou desmarcar uma linha. Repetições e linhas
inválidas impedem o preenchimento até revisão. Jogos existentes, iniciados ou
fechados recebem alertas textuais; após desistência, são bloqueados. Mensagem
totalmente irreconhecível não preenche nada. Participante é escolhido manualmente,
sem inferência automática pelo nome na mensagem.

Confirmar prévia apenas preenche o formulário. A gravação ocorre depois, usando
Salvar e ficar ou Salvar e próximo. O texto original é vinculado por assinatura
ao administrador, bolão, pessoa e rodada, com validade de duas horas. Cada palpite
importado recebe `texto_original_whatsapp` no JSON `valores_novos` do PalpiteLog,
inclusive quando o placar é igual ao existente. Origem continua responsavel.
Não houve migração nem alteração de campos/endpoints anteriores. Nova rota:
`admin.previa_whatsapp`, POST `/b/<bolao>/palpites/previa-whatsapp`.

Limites: 20.000 caracteres e 200 linhas por mensagem. Times não reconhecidos
exigem seleção manual; não são adivinhados. A prévia requer JavaScript.

Validação: 269 testes passaram; formatos pedidos, duplicidade, ambiguidade,
apelidos, autorização, token adulterado e auditoria cobertos. No navegador,
uma mensagem foi revisada e preenchida sem nenhuma escrita (digest da cópia
igual ao original); o salvamento posterior criou dois palpites e seus logs
somente na cópia isolada. O banco real permaneceu inalterado.
