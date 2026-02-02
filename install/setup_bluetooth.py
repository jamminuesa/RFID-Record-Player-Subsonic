import subprocess
import time
import sys
import os

def run_command(command):
    """Ejecuta comando y devuelve salida, ignorando errores no críticos."""
    try:
        return subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL).decode('utf-8')
    except:
        return ""

def ensure_bluetooth_ready():
    print("🔄 Reiniciando servicio Bluetooth...")
    subprocess.run(
        ["systemctl", "restart", "bluetooth"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("📡 Desbloqueando Bluetooth (rfkill)...")
    subprocess.run(
        ["rfkill", "unblock", "bluetooth"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)


def scan_devices(timeout=SCAN_TIME):
    print(f"\n🔍 Escaneando dispositivos ({timeout}s)...")

    process = subprocess.Popen(
        ["bluetoothctl"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1
    )

    devices = {}

    def send(cmd):
        process.stdin.write(cmd + "\n")
        process.stdin.flush()

    send("agent on")
    send("default-agent")
    send("scan on")

    start = time.time()

    while time.time() - start < timeout:
        line = process.stdout.readline()
        if not line:
            continue

        # DEBUG opcional:
        # print("DEBUG:", line.strip())

        match = re.search(r"Device ([0-9A-F:]{17}) (.+)", line)
        if match:
            mac, name = match.groups()
            devices[mac] = name

    send("scan off")
    send("exit")
    process.wait()

    return devices


def pair_and_connect(mac, name):
    print(f"\n🔗 Emparejando con {name} ({mac})...")

    process = subprocess.Popen(
        ["bluetoothctl"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )

    def send(cmd):
        print(f"   > {cmd}")
        process.stdin.write(cmd + "\n")
        process.stdin.flush()
        time.sleep(1)

    send("power on")
    send("agent on")
    send("default-agent")
    send("pairable on")
    send(f"pair {mac}")
    send(f"trust {mac}")
    send(f"connect {mac}")
    send("exit")

    process.wait()
    print("✅ Emparejado, trusted y conectado correctamente.")

def install_autoconnect_service(mac):
    script_path = "/usr/local/bin/bt-autoconnect.sh"
    service_path = "/etc/systemd/system/bt-autoconnect.service"

    script = f"""#!/bin/bash
sleep 5
for i in {{1..10}}; do
    bluetoothctl power on
    bluetoothctl connect {mac} && exit 0
    sleep 3
done
exit 1
"""

    service = """[Unit]
Description=Bluetooth Auto Connect Headphones
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/local/bin/bt-autoconnect.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

    with open(script_path, "w") as f:
        f.write(script)
    os.chmod(script_path, 0o755)

    with open(service_path, "w") as f:
        f.write(service)

    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", "bt-autoconnect.service"])
    subprocess.run(["systemctl", "start", "bt-autoconnect.service"])

    print("⚙️ Servicio de auto-conexión instalado y activado.")



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
