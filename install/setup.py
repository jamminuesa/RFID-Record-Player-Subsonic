import sys
import spotipy
import json
from dotenv import set_key
from mfrc522 import SimpleMFRC522
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler

ENV_FILE = ".env"
RFID_FILE = "rfid.json"

def read_rfid_file():
    rfid_map = {}
    try:
        with open(RFID_FILE, 'r') as file:
            rfid_map = json.load(file)
    except FileNotFoundError:
        print("Error: file not found, creating a new rfid_map file.")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    return rfid_map

def write_rfid_file(rfid_map):
    with open(RFID_FILE, "w") as json_file:
        json.dump(rfid_map, json_file, indent=4)
    
def set_up_spotify_credentials():
    client_id = input("Enter Spotify Client ID: ").strip()
    client_secret = input("Enter Spotify Client Secret: ").strip()
    redirect_uri = input("Enter Redirect URI: ").strip()

    cache_handler = MemoryCacheHandler()
    auth = SpotifyOAuth(
        scope = 'user-read-playback-state,user-modify-playback-state,user-read-recently-played',
        client_id = client_id,
        client_secret = client_secret,
        redirect_uri = redirect_uri,
        open_browser = False,
        cache_handler = cache_handler
    )
    auth.get_access_token(as_dict=False)
    token_info = cache_handler.get_cached_token()
    if not token_info or not token_info.get('refresh_token'):
        sys.exit("Error: Unable to get Spotify refresh token.")
    refresh_token = token_info['refresh_token']
    
    set_key(ENV_FILE, "SPOTIFY_CLIENT_ID", client_id)
    set_key(ENV_FILE, "SPOTIFY_CLIENT_SECRET", client_secret)
    set_key(ENV_FILE, "SPOTIFY_REFRESH_TOKEN", refresh_token)
    set_key(ENV_FILE, "SPOTIFY_REDIRECT_URI", redirect_uri)
    print("Spotify credentials set.")

def write_rfid_tags():
    rfid = SimpleMFRC522()
    rfid_map = read_rfid_file()

    while True:
        print("Please scan RFID tag:")
        rfid_id = str(rfid.read_id())

        print(f"RFID ID {rfid_id} detected, enter spotify track, artist, album, or playlist uri:")
        # Get user input as a string
        uri = input("Spotify URI: ")

        if not uri or not uri.startswith("spotify:") or uri.split(":")[1] not in ["track", "album", "playlist", "artist"]:
            print("Invalid URI, spotify URI's must be in the format spotify:{track/album/playlist/artist}:{id}")
        else:
            rfid_map[rfid_id] = uri
            write_rfid_file(rfid_map)
            print(f"Stored URI for RFID ID {rfid_id}")
        
        print("Please choose an option:")
        print("1. Add another RFID tag")
        print("2. Exit")
        choice = input("Enter your choice: ")
        if choice == "2":
            break

def read_rfid_tags():
    rfid = SimpleMFRC522()
    rfid_map = read_rfid_file()

    while True:
        print("Please scan RFID tag:")
        rfid_id = str(rfid.read_id())

        if rfid_id in rfid_map:
            print(f"RFID ID {rfid_id} is mapped to {rfid_map.get(rfid_id)}.")
        else:
            print(f"RFID ID {rfid_id} is not configured.")
        
        print("Please choose an option:")
        print("1. Read another RFID tag")
        print("2. Exit")
        choice = input("Enter your choice: ")
        if choice == "2":
            break

def get_user_choice():
    actions = {
        "1": ("Setup Spotify credentials", set_up_spotify_credentials),
        "2": ("Write RFID tags", write_rfid_tags),
        "3": ("Read RFID tags", read_rfid_tags)
    }

    exit_key = str(len(actions) + 1)

    while True:
        print("\nPlease choose an option:")
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print(f"{exit_key}. Exit")

        choice = input("Enter your choice: ").strip()

        if choice == exit_key:
            print("Exiting the program.")
            break

        action = actions.get(choice)
        if not action:
            print("Invalid choice. Please try again.")
            continue

        label, func = action
        print(f"You selected: {label}")
        func()


if __name__ == "__main__":
    get_user_choice()