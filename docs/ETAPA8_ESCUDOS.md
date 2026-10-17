# Etapa 8 — Escudo local e overrides

A imagem enviada foi copiada sem edição para `static/escudos/athletico-pr.png`.
SHA-256 da origem e cópia: A74511AD022B00409CF2FA3A36D8F17240865243CACB0FCA14D2CC48F145BF43.
Consulta ao endpoint real `/v4/teams/1768` confirmou ID 1768, nome CA Paranaense,
shortName Paranaense e crest https://crests.football-data.org/1768.png.
O token foi usado somente na requisição autenticada, sem inclusão em arquivos ou logs.

Edite `config_escudos.py` para configurar ID da API ou nome normalizado e caminho
relativo a static/ (ou URL HTTPS). `services/escudos.py` centraliza a resolução:
override local existente, override HTTPS, crest da API e iniciais. O template
compartilhado `partials/escudo.html` trata falhas de carregamento.
Jogos sem ID do clube usam nomes normalizados e o cache já existente do campeonato;
não há consultas de rede durante a renderização.

Aplicado na tabela, jogos, grade de palpites, lançamento rápido e telas legadas
de palpites. O ranking do bolão lista pessoas e não contém escudos de clubes.
Nenhum escudo dos outros times foi substituído. Os demais 19 escudos carregaram
na revisão visual; nenhum outro claramente desatualizado foi identificado.
Essa revisão não certifica pequenas mudanças recentes de identidade visual.

Athletico é servido localmente. Outros escudos permanecem na fonte HTTPS da API;
não foi necessário copiá-los. Novos arquivos locais podem ser configurados pelo
mesmo mecanismo, sem migrar o banco.

Validação: testes de prioridade, arquivo ausente, nomes alternativos, isolamento
por campeonato e segurança de caminhos; suíte completa executada. Conferência
visual do arquivo local carregado e de todos os escudos da tabela. Sem migração
ou alteração dos dados reais.
