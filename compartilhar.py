import os
import sys
import time
import socket
import subprocess
from pyngrok import ngrok, conf
from pyngrok.exception import PyngrokNgrokError


def is_port_in_use(port=5000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def is_token_configured():
    config_paths = [
        conf.DEFAULT_NGROK_CONFIG_PATH,
        os.path.expanduser("~/.config/ngrok/ngrok.yml"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ngrok", "ngrok.yml"),
    ]
    for path in config_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    if "authtoken:" in f.read():
                        return True
            except Exception:
                pass
    return False


def pedir_token():
    print("\n" + "-" * 60)
    print("🔑 O ngrok precisa do seu token gratuito para criar o link.")
    print("1. Acesse: https://dashboard.ngrok.com/signup (pode entrar com Google)")
    print("2. Copie seu token em: https://dashboard.ngrok.com/get-started/your-authtoken")
    print("-" * 60)
    token = input("\nCole seu authtoken aqui e aperte Enter: ").strip()
    if not token:
        print("Nenhum token informado. Operação cancelada.")
        sys.exit(1)
    ngrok.set_auth_token(token)
    print("✅ Token salvo com sucesso!\n")


def main():
    print("=" * 60)
    print("      COMPARTILHAR BOLÃO NA WEB COM SEU AMIGO")
    print("=" * 60)

    # 1. Garante que o servidor Flask está rodando
    flask_process = None
    if not is_port_in_use(5000):
        print("\nIniciando o servidor local do Bolão na porta 5000...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        flask_process = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=script_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Aguarda 2 segundos para o Flask subir
        for _ in range(10):
            if is_port_in_use(5000):
                break
            time.sleep(0.5)

    # 2. Verifica se o authtoken já foi salvo
    if not is_token_configured():
        pedir_token()

    # 3. Inicia o túnel ngrok
    print("\nConectando à internet...")
    try:
        tunnel = ngrok.connect(5000, "http")
        public_url = tunnel.public_url

        print("\n" + "=" * 60)
        print("🚀 SITE ONLINE COM SUCESSO!")
        print("=" * 60)
        print(f"\nLink público para enviar ao seu amigo:\n\n👉  {public_url}\n")
        print("=" * 60)
        print("DICAS:")
        print("• Seu amigo pode abrir esse link no celular ou no computador.")
        print("• Mantenha esta janela aberta enquanto ele estiver navegando.")
        print("• Pressione Ctrl + C aqui no terminal para encerrar quando terminar.")
        print("=" * 60 + "\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nEncerrando túnel e servidor...")
    except PyngrokNgrokError as e:
        msg = str(e)
        if "authtoken" in msg.lower() or "ERR_NGROK_4018" in msg:
            print("\n❌ Erro de autenticação do ngrok. Vamos recadastrar seu token:")
            pedir_token()
            print("Execute o comando novamente: python compartilhar.py")
        else:
            print(f"\nErro ao iniciar túnel: {e}")
    except Exception as e:
        print(f"\nErro ao iniciar túnel: {e}")
    finally:
        try:
            ngrok.kill()
        except Exception:
            pass
        if flask_process:
            try:
                flask_process.terminate()
            except Exception:
                pass
        print("Concluído. Tudo foi encerrado com sucesso.")


if __name__ == "__main__":
    main()
