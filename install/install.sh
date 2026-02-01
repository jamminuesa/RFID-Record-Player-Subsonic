#!/bin/bash

set -e

# Detectar el directorio raíz del proyecto (padre de 'install')
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "==========================================="
echo "   INSTALADOR DE RPI NAVIDROME PLAYER      "
echo "==========================================="
echo "📂 Directorio del proyecto detectado: $PROJECT_ROOT"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python3 is not installed. Please install it first."
    exit 1
fi

# 1. ACTUALIZAR E INSTALAR DEPENDENCIAS DE SISTEMA
echo "📦 Instalando dependencias del sistema (VLC, Bluetooth, Python)..."
sudo apt-get install -y swig liblgpio-dev \
    vlc \
    bluez pulseaudio-module-bluetooth \
    git > /dev/null

# 2. ARREGLAR BLOQUEO DE BLUETOOTH (Tu petición)
echo "🔓 Desbloqueando RFKill para Bluetooth..."
sudo rfkill unblock bluetooth
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "🐍 Creando entorno virtual en $PROJECT_ROOT/venv..."
    python3 -m venv venv
fi

echo "📥 Instalando librerías de Python..."
source "$PROJECT_ROOT/venv/bin/activate"
pip install -r install/requirements.txt -qq > /dev/null

echo "🔌 Habilitando interfaz SPI..."
sudo sed -i 's/^dtparam=spi=.*/dtparam=spi=on/' /boot/config.txt
sudo sed -i 's/^#dtparam=spi=.*/dtparam=spi=on/' /boot/config.txt
sudo raspi-config nonint do_spi 0

# 6. CREAR SERVICIO SYSTEMD (AUTO-ARRANQUE)
echo "⚙️ Configurando servicio de auto-arranque (systemd)..."
SERVICE_FILE="/etc/systemd/system/recordplayer.service"

# Creamos el archivo del servicio dinámicamente con las rutas correctas
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Navidrome RFID Record Player
After=network.target sound.target bluetooth.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT
# Activamos el entorno virtual y ejecutamos el script
ExecStart=$PROJECT_ROOT/venv/bin/python $PROJECT_ROOT/install/record_player.py
# Reiniciar automáticamente si falla (ej: si se pierde internet momentáneamente)
Restart=always
RestartSec=5
# Variables de entorno importantes para audio y video en headless
Environment=PYTHONUNBUFFERED=1
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u)

[Install]
WantedBy=multi-user.target
EOF

# Recargar demonio y habilitar servicio
sudo systemctl daemon-reload
sudo systemctl enable recordplayer.service

# Crear archivo env
# Pedir datos al usuario
read -p "Introduce la URL de Subsonic: " SUBSONIC_URL
read -p "Introduce el puerto de Subsonic: " SUBSONIC_PORT
read -p "Introduce el usuario de Navidrome: " SUBSONIC_USER
read -s -p "Introduce la contraseña de Navidrome: " SUBSONIC_PASS
echo ""

# Crear el archivo .env
cat <<EOF > "$PROJECT_ROOT/.env"
SUBSONIC_URL=$SUBSONIC_URL
SUBSONIC_PORT=$SUBSONIC_PORT
SUBSONIC_USER=$SUBSONIC_USER
SUBSONIC_PASS=$SUBSONIC_PASS
EOF

echo "Archivo .env creado correctamente ✅"


echo "==========================================="
echo "✅ INSTALACIÓN COMPLETADA"
echo "==========================================="
echo "Pasos siguientes:"
echo "1. Ejecuta 'python3 install/setup_bluetooth.py' para conectar tus cascos."
echo "2. Reinicia la Raspberry Pi ('sudo reboot')."
echo "3. ¡El tocadiscos arrancará solo!"
echo ""
