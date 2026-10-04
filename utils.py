"""
Utilitários compartilhados da aplicação.
"""
import re
from werkzeug.security import generate_password_hash, check_password_hash


def validar_email(email):
    """Valida formato de email."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validar_senha(senha):
    """
    Valida força da senha.
    Requer pelo menos 6 caracteres.
    """
    if not senha or len(senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres."
    return True, ""


def validar_nome(nome):
    """Valida que o nome não está vazio."""
    if not nome or not nome.strip():
        return False
    return len(nome.strip()) >= 2


def hash_senha(senha):
    """Gera hash da senha."""
    return generate_password_hash(senha)


def verificar_senha(senha, hash_senha):
    """Verifica se a senha corresponde ao hash."""
    return check_password_hash(hash_senha, senha)


def validar_arquivo_upload(filename, allowed_extensions):
    """Valida extensão do arquivo enviado."""
    if not filename:
        return False, "Nenhum arquivo enviado."

    if '.' not in filename:
        return False, "Arquivo sem extensão."

    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        return False, f"Extensão não permitida. Use: {', '.join(allowed_extensions)}"

    return True, ""


def normalizar_texto(texto):
    """Remove espaços extras e normaliza texto."""
    if not texto:
        return ""
    return texto.strip()
