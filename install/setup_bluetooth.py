import subprocess
import time
import sys
import os

def run_command(command):
    """Ejecuta un comando de shell y devuelve la salida."""
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        return None

def main():
    print("========================================")
    print("   ASISTENTE DE EMPAREJAMIENTO BT       ")
    print("========================================")
    print("1. Asegúrate de que tus cascos/altavoz están en MODO EMPAREJAMIENTO (parpadeando).")
    input("👉 Pulsa ENTER cuando estén listos...")

    print("\n🔍 Escaneando dispositivos (espera 10s)...")

    # Iniciar escaneo en segundo plano
    try:
        subprocess.Popen(["bluetoothctl", "scan", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10)
        # Obtener dispositivos
        devices_raw = run_command("bluetoothctl devices")
    finally:
        # Parar escaneo para que no moleste
        subprocess.run(["bluetoothctl", "scan", "off"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not devices_raw:
        print("❌ No se encontraron dispositivos. Inténtalo de nuevo.")
        return

    devices = []
    print("\n🎧 Dispositivos encontrados:")
    lines = devices_raw.split('\n')
    for i, line in enumerate(lines):
        # Formato: Device XX:XX:XX:XX:XX:XX Name
        parts = line.split(' ', 2)
        if len(parts) >= 3:
            mac = parts[1]
            name = parts[2]
            devices.append((mac, name))
            print(f"{i + 1}. {name} ({mac})")

    choice = input("\n👉 Selecciona el número de tu dispositivo: ")
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(devices):
            print("Número inválido.")
            return

        target_mac, target_name = devices[idx]
        print(f"\n🔗 Intentando emparejar con {target_name}...")

        # Secuencia de comandos bluetoothctl
        print(f"   - Trusting {target_mac}...")
        run_command(f"bluetoothctl trust {target_mac}")

        print(f"   - Pairing {target_mac}...")
        pair_res = run_command(f"bluetoothctl pair {target_mac}")

        print(f"   - Connecting {target_mac}...")
        connect_res = run_command(f"bluetoothctl connect {target_mac}")

        print("\n✅ ¡Configuración terminada!")
        print("El dispositivo ha sido marcado como 'Trusted'.")
        print("La Raspberry Pi debería conectarse automáticamente a él al reiniciar.")

        # Guardar la MAC para forzar conexión si fuera necesario en el futuro
        with open("bluetooth_mac.txt", "w") as f:
            f.write(target_mac)

    except ValueError:
        print("Entrada no válida.")

if __name__ == "__main__":
    # Asegurarse de correr como root/sudo para bluetooth
    if os.geteuid() != 0:
        print("⚠️  Por favor, ejecuta este script con sudo:")
        print("   sudo python3 install/setup_bluetooth.py")
        sys.exit(1)
    main()
