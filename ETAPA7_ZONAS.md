# Etapa 7 — Zonas da classificação

Faixas aprovadas preservadas em `config_zonas.py`:

| Faixa | Zona | Cor |
|---|---|---|
| 1–4 | Fase de Grupos Libertadores | Verde #4ade80 |
| 5–6 | Pré-Libertadores | Azul #60a5fa |
| 7–12 | Copa Sul-Americana | Amarelo #fbbf24 |
| 17–20 | Rebaixamento | Vermelho #f87171 |

A cor única de cada zona alimenta barra interna de 4px, fundo com 8% de opacidade,
marcador de posição e quadrado da legenda. As classes dinâmicas vindas do Python
foram substituídas por variáveis CSS; elas não eram incluídas no build do Tailwind.
Rótulo e faixa continuam na configuração, sem posições fixadas no template.
Linhas possuem title e aria-label com a zona; a legenda permanece textual.
O mesmo renderizador atende outras competições configuradas sem mudar suas faixas.

Validação: seis testes existentes da classificação passaram; CSS recompilado;
conferência no tema escuro atual com as 20 equipes do cache, quatro cores e barras
de 4px confirmadas pelo navegador. Cores da legenda têm contraste maior que 3:1
contra o fundo do cartão. Não existe tema claro alternativo no visual atual.
Banco original e cópia permaneceram idênticos. Sem migração, alteração de API,
endpoints ou regras de classificação. Captura em instance/zonas-etapa7.png.
