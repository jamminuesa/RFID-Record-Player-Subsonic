import libsonic
import vlc
import time
import os
import sys
import string
import random
import hashlib
from urllib.parse import quote
from dotenv import load_dotenv

# Cargar credenciales
load_dotenv()

SERVER = os.getenv("SUBSONIC_URL")
USER = os.getenv("SUBSONIC_USER")
PASS = os.getenv("SUBSONIC_PASS")

def generate_salt(length=8):
    """
    Genera un salt aleatorio con letras y números.

    Args:
        length (int): longitud del salt, mínimo recomendado 6

    Returns:
        str: salt aleatorio
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


# -------------------------------
# Función para generar token MD5
# -------------------------------
def generate_auth_token(password, salt):
    """
    Calcula el token de autenticación MD5 según la API de Subsonic.

    Args:
        password (str): la contraseña del usuario
        salt (str): el salt aleatorio generado

    Returns:
        str: token MD5 hexadecimal en minúsculas
    """
    md5_input = (password + salt).encode('utf-8')
    token = hashlib.md5(md5_input).hexdigest()
    return token


# -------------------------------
# Función combinada para usar directamente
# -------------------------------
def get_auth(password, salt_length=8):
    """
    Genera un salt y un token MD5 listo para usar en la URL de Subsonic.

    Args:
        password (str): contraseña del usuario
        salt_length (int): longitud del salt aleatorio

    Returns:
        tuple: (token, salt)
    """
    salt = generate_salt(salt_length)
    token = generate_auth_token(password, salt)
    return token, salt

def main():
    if not all([SERVER, USER, PASS]):
        print("Error: Faltan datos en el archivo .env")
        return

    print(f"📡 Conectando a {SERVER} con usuario {USER}...")

    # 1. Conexión con Subsonic
    try:
        conn = libsonic.Connection(SERVER, USER, PASS, port=443, appName="RPiPlayer")
        if not conn.ping():
            print("❌ Fallo al conectar con el servidor. Revisa IP y puerto.")
            return
        print("✅ Conexión establecida.")
    except Exception as e:
        print(f"❌ Error crítico de conexión: {e}")
        return

    # 2. Obtener algo para reproducir (Un álbum aleatorio)
    print("🔍 Buscando una canción aleatoria...")
    try:
        # Pedimos 1 álbum aleatorio
        first_song = conn.getRandomSongs(size=1)

    except Exception as e:
        print(f"❌ Error recuperando datos de Subsonic: {e}")
        return

    # 3. Configurar VLC y Reproducir
    # IMPORTANTE: Construimos la URL manualmente porque VLC necesita acceder
    # directamente al stream con las credenciales en la URL.
    try:
        song = first_song['randomSongs']['song'][0]
        token, salt = get_auth(PASS)
        # _getAuth() genera los parámetros ?u=user&t=token&s=salt&v=version&c=client
        print(f"Canción {song['title']} con id {song['id']}")
        auth = conn.stream(song['id'])
        stream_url = f"{SERVER}/rest/stream?id={song['id']}&u={quote(USER)}&t={token}&s={salt}&v=1.16.1&c=RPiPlayer>
        print(f"{stream_url}")
        print("▶ Reproduciendo vía Bluetooth...")
        # Inicializar VLC
        instance = vlc.Instance()
        player = instance.media_player_new()
        media = instance.media_new(stream_url)
        player.set_media(media)
        player.play()

        # Esperar un poco para asegurar que el buffer carga
        time.sleep(2)

        # Bucle para mantener el script vivo mientras suena la canción
        duration = song.get('duration', 30) # Si no hay duración, asume 30s
        print(f"   (Duración aprox: {duration} segundos - Pulsa Ctrl+C para parar)")

        while player.is_playing():
            time.sleep(1)

        print("⏹ Reproducción finalizada.")

    except Exception as e:
        print(f"❌ Error en VLC: {e}")
    except KeyboardInterrupt:
        print("\n⏹ Deteniendo...")
        player.stop()

if __name__ == "__main__":
    main()



