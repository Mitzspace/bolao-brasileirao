# Primeiro marcador automático e conferência dos bônus

## Preenchimento automático

O primeiro marcador dos jogos **clássicos/especiais** é preenchido pela ESPN (gratuita, sem chave):

- vale o autor do primeiro gol do jogo, **inclusive gol contra**; gols da disputa de pênaltis não contam;
- o que um responsável já digitou **nunca é sobrescrito**;
- jogos comuns e jogos 0x0 não recebem marcador;
- o placar da ESPN precisa bater com o lançado; se não bater, nada é preenchido.

Campeonatos da ESPN recebem o marcador na mesma consulta dos placares. Campeonatos da
football-data/API-Football consultam o placar do dia na ESPN só quando há clássico dos últimos
7 dias encerrado sem marcador (no máximo uma consulta por dia de jogo a cada hora). O
casamento é pelos times (nomes normalizados como na sincronização) e pela data, com
tolerância de 2 dias. A tabela `LIGAS_ESPN` em `services/primeiro_gol.py` liga os códigos
(BSA, 71, CLI…) às ligas da ESPN.

A ESPN escreve o nome como ela conhece o jogador (ex.: "José Manuel López", "Giorgian de
Arrascaeta"). Pela regra de `mesmo_jogador`, um palpite só com parte do nome ("López") não
pontua. Revise esses casos no relatório de quase acertos e, se preferir, edite o marcador.

## Conferência dos jogos já disputados

Os bônus da planilha estão em `BonusRodada` (crédito por rodada, sem o jogo). O comando
abaixo preenche os marcadores dos clássicos antigos, recalcula o bônus palpite a palpite e
compara com o crédito da planilha.

```bash
pg_dump ...                                        # backup antes de aplicar
python -m scripts.conferir_primeiro_gol            # simulação + CSVs, nada é gravado
python -m scripts.conferir_primeiro_gol --aplicar  # grava, após confirmação
```

| Situação | O que significa | Ao aplicar |
| --- | --- | --- |
| Planilha confere | Recalculado = crédito | Crédito zera; o bônus passa a aparecer nos jogos. Total igual |
| Planilha deu mais | Recalculado < crédito | Fica no crédito só a diferença. Total igual |
| Palpites justificam mais | Recalculado > crédito | Crédito zera. **Total sobe** |
| Sem palpite de 1º gol | Crédito numa rodada sem palpites de 1º gol no sistema | Nada muda |
| Bônus novo | Rodada sem crédito em que o marcador gera bônus | **Total sobe** |

Arquivos gerados (na pasta indicada no fim da execução): `bolaoN-jogos.csv` (marcador de
cada clássico e de onde veio), `bolaoN-pessoas.csv` (crédito, recalculado, variação de pontos)
e `bolaoN-quase-acertos.csv` (palpites com nome parecido que a regra não aceita).
