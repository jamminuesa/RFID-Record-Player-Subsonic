import sys
import json
import time
import os
import libsonic
from dotenv import load_dotenv
from pathlib import Path
from mfrc522 import SimpleMFRC522


# --- GESTIÓN DE RUTAS (PATHS) ---
# Obtenemos la ruta donde está este script (carpeta /install)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Obtenemos la ruta padre (carpeta raíz del proyecto)
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))

# Archivos de configuración
ENV_FILE = os.path.join(ROOT_DIR, ".env")
RFID_FILE = os.path.join(ROOT_DIR, "rfid.json")

# Cargar credenciales
load_dotenv(ENV_FILE)

SERVER = os.getenv("SUBSONIC_URL")
PORT = os.getenv("SUBSONIC_PORT")
USER = os.getenv("SUBSONIC_USER")
PASS = os.getenv("SUBSONIC_PASS")

def connect_subsonic():
    """Establece conexión con el servidor Subsonic"""
    if not all([SERVER, USER, PASS]):
        print("❌ Error: Faltan datos en el archivo .env")
        sys.exit(1)

    try:
        conn = libsonic.Connection(SERVER, USER, PASS, port= PORT, appName="JukePi")
        if not conn.ping():
            print("❌ No se pudo conectar a Subsonic. Verifica tu .env")
            sys.exit(1)
        return conn
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        sys.exit(1)

def read_rfid_file():
    """Lee el archivo JSON actual o crea uno vacío"""
    rfid_map = {}
    try:
        with open(RFID_FILE, 'r') as file:
            rfid_map = json.load(file)
    except FileNotFoundError:
        print(f"ℹ Creando nuevo archivo {RFID_FILE}...")
    except json.JSONDecodeError:
        print("⚠ Error leyendo JSON, se iniciará uno nuevo.")
    return rfid_map

def write_rfid_file(rfid_map):
    """Guarda los cambios en el archivo JSON"""
    with open(RFID_FILE, "w") as json_file:
        json.dump(rfid_map, json_file, indent=4)
    print("✅ Guardado correctamente en rfid.json")

def search_and_select(conn, search_type):
    """Buscador interactivo de Subsonic"""
    if search_type == "playlist":
        # Las playlists se listan directamente, no se buscan por texto
        print("\n📥 Obteniendo playlists...")
        playlists = conn.getPlaylists().get('playlists', {}).get('playlist', [])

        if not playlists:
            print("❌ No tienes playlists creadas en Subsonic.")
            return None

        print("\n--- Playlists encontradas ---")
        for idx, pl in enumerate(playlists):
            print(f"{idx + 1}. {pl['name']} (Canciones: {pl.get('songCount', 0)})")

        return select_item(playlists, "playlist")

    else:
        while True:

            # Búsqueda de Album o Artista
            query = input(f"\n🔍 Introduce el nombre del {search_type} a buscar: ")
            print("Buscando...")

            # Subsonic API search3 devuelve resultados anidados
            results = conn.search3(query)
            items = []

            if search_type == "album" and 'album' in results.get('searchResult3', {}):
                items = results['searchResult3']['album']
            elif search_type == "artist" and 'artist' in results.get('searchResult3', {}):
                items = results['searchResult3']['artist']

            if not items:
                print("❌ No se encontraron resultados.")
                continue

            print(f"\n--- Resultados para '{query}' ---")
            for idx, item in enumerate(items[:10]): # Limitamos a 10 resultados
                name = item.get('name') or item.get('title') # Album usa title, Artist usa name
                artist = item.get('artist', '')
                extra_info = f"- {artist}" if artist else ""
                print(f"{idx + 1}. {name} {extra_info}")

            return select_item(items[:10], search_type)

def select_item(items, type_label):
    """Ayudante para elegir un número de la lista"""
    while True:
        try:
            choice = input("\n👉 Selecciona el número (o 0 para cancelar): ")
            idx = int(choice) - 1
            if idx == -1:
                return None
            if 0 <= idx < len(items):
                selected = items[idx]
                name = selected.get('name') or selected.get('title')
                item_id = selected['id']
                # Formato de guardado: subsonic:tipo:id
                return f"subsonic:{type_label}:{item_id}", name
            print("❌ Número inválido.")
        except ValueError:
            print("❌ Por favor introduce un número.")

def write_rfid_tags(conn):
    #rfid_reader = SimpleMFRC522()
    rfid_map = read_rfid_file()

    while True:
        print("\n==================================")
        print("   PROGRAMADOR DE ETIQUETAS NFC   ")
        print("==================================")
        print("Acerca una tarjeta o llavero al lector...")

        try:
            rfid_id = 856425748622 #rfid_id, _ = rfid_reader.read() # read() devuelve id y texto, solo queremos ID
            rfid_id = str(rfid_id)
            print(f"🔔 ¡Etiqueta detectada! ID: {rfid_id}")

            # Verificar si ya existe
            if rfid_id in rfid_map:
                print(f"⚠ Esta etiqueta ya está asignada a: {rfid_map[rfid_id]}")
                overwrite = input("¿Deseas sobrescribirla? (s/n): ").lower()
                if overwrite != 's':
                    continue

            print("\n¿Qué quieres asignar a esta etiqueta?")
            print("1. Álbum")
            print("2. Artista")
            print("3. Playlist")
            print("4. Cancelar")

            opcion = input("Opción: ")

            uri = None
            name = None

            if opcion == "1":
                result = search_and_select(conn, "album")
                if result: uri, name = result
            elif opcion == "2":
                result = search_and_select(conn, "artist")
                if result: uri, name = result
            elif opcion == "3":
                result = search_and_select(conn, "playlist")
                if result: uri, name = result
            elif opcion == "4":
                continue
            else:
                print("Opción no válida.")

            if uri:
                rfid_map[rfid_id] = uri
                write_rfid_file(rfid_map)
                print(f"✨ ¡Éxito! Etiqueta {rfid_id} vinculada a: {name}")

        except Exception as e:
            print(f"Error leyendo tarjeta: {e}")
            time.sleep(1)

        continuar = input("\n¿Programar otra etiqueta? (s/n): ").lower()
        if continuar != 's':
            break

def read_rfid_mode():
    rfid = SimpleMFRC522()
    rfid_map = read_rfid_file()

    print("\n--- MODO LECTURA (Ctrl+C para salir) ---")
    print("Acerca una tarjeta para ver qué tiene asignado.")

    try:
        while True:
            rfid_id, _ = rfid.read()
            rfid_id = str(rfid_id)
            if rfid_id in rfid_map:
                print(f"ID: {rfid_id} -> {rfid_map[rfid_id]}")
            else:
                print(f"ID: {rfid_id} -> [VACÍA / NO CONFIGURADA]")
            time.sleep(1)
    except KeyboardInterrupt:
        return

def main():
    conn = connect_subsonic()

    while True:
        print("\n=== MENÚ PRINCIPAL ===")
        print("1. Programar etiquetas (Buscar y Asignar)")
        print("2. Leer etiquetas (Verificación)")
        print("3. Salir")

        choice = input("Elige una opción: ")

        if choice == "1":
            write_rfid_tags(conn)
        elif choice == "2":
            read_rfid_mode()
        elif choice == "3":
            print("Adiós 👋")
            break
        else:
            print("Opción inválida")

if __name__ == "__main__":
    main()
