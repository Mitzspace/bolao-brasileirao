# Migração — o que mudou nesta versão

## Novas colunas no banco

Duas novas colunas foram adicionadas aos models:

- `participante.admin` (BOOLEAN, default FALSE)
- `jogo.encerrado` (BOOLEAN, default FALSE)

**Em bancos novos** o `db.create_all()` cria tudo automaticamente.

**Em bancos existentes** rode no `flask shell` (ou num script) antes de subir:

```python
import sqlite3
conn = sqlite3.connect("instance/banco.db")
try:
    conn.execute("ALTER TABLE participante ADD COLUMN admin BOOLEAN NOT NULL DEFAULT 0")
except:
    pass
try:
    conn.execute("ALTER TABLE jogo ADD COLUMN encerrado BOOLEAN NOT NULL DEFAULT 0")
except:
    pass
conn.commit()
conn.close()
print("Migração concluída.")
```

## Criar o primeiro admin

Depois de rodar a aplicação e criar sua conta normalmente pelo `/cadastro`,
promova-a pelo `flask shell`:

```python
from app import create_app
from database import db
from models import Participante

app = create_app()
with app.app_context():
    p = Participante.query.filter_by(email="seu@email.com").first()
    p.admin = True
    db.session.commit()
    print(f"{p.nome} agora é admin.")
```

Depois disso o botão **Admin** aparece na barra de navegação e você pode
promover outros participantes pela interface em `/admin/participantes`.

## CSS

O arquivo de estilo agora fica em `static/css/style.css` (antes era `static/style.css`).
Atualize a pasta `static/` copiando o arquivo para o lugar certo.
