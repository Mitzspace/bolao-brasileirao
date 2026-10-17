# Vários campeonatos no mesmo bolão

Cada campeonato do bolão é guardado como um bolão próprio, ligado ao bolão principal
pela coluna `bolao.grupo_id`. Assim, jogos, rodadas, palpites e classificação de cada
campeonato ficam totalmente separados, usando as mesmas regras já testadas.

- Criar: aba **Campeonatos** → **Novo campeonato**. Participantes e responsáveis ativos
  do campeonato atual são copiados; palpites, jogos e créditos não.
- Alternar: seletor de campeonato no topo das telas (aparece com 2+ campeonatos),
  botões da aba Campeonatos ou a aba Bolões.
- Participante adicionado depois em um campeonato não é incluído automaticamente nos
  outros: cadastre-o também no outro campeonato, se for o caso.

## Migração obrigatória (uma vez, com backup)

O sistema não inicia sem a coluna nova.

SQLite local (cria backup ao lado do banco e pode ser executado de novo):

```powershell
.venv\Scripts\python.exe -m migrations.grupo_bolao instance/banco.db
```

PostgreSQL (Neon), **antes** de publicar o código no Render: faça backup (branch do Neon)
e execute no SQL Editor o arquivo `migrations/sql/005_grupo_bolao.sql`:

```sql
BEGIN;
ALTER TABLE bolao ADD COLUMN IF NOT EXISTS grupo_id INTEGER REFERENCES bolao(id);
COMMIT;
```

## Atualização: cada campeonato é um bolão separado

A interface não cria mais campeonatos dentro do mesmo bolão. Para um novo
campeonato, use **Bolões › Novo bolão**. Os grupos já existentes são desfeitos por:

- Local (SQLite, faz backup): `python -m migrations.separar_campeonatos instance/banco.db`
- Neon: rode `migrations/sql/006_separar_campeonatos.sql` no SQL Editor (após backup).

Bolões extras com o mesmo nome do principal passam a se chamar "<campeonato> <temporada>"
(ex.: "Copa do Brasil 2026"). Palpites, jogos, participantes e pontos não mudam.
A coluna `grupo_id` e `services/grupos_bolao.py` ficam para a ideia futura de vários
campeonatos no mesmo bolão (que exigirá trocar de campeonato também na aba Jogos).
