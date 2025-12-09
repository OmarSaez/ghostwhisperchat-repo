Este es el desarrollo de un Chat LAN para uso interno de forma simple

# INSTALADOR
echo "deb [trusted=yes] https://omarsaez.github.io/ghostwhisperchat-repo/ stable main" | sudo tee /etc/apt/sources.list.d/ghostwhisperchat.list

sudo apt update

sudo apt install ghostwhisperchat


# AUTOLEVANTADO
nano ~/autostart_ghostwhisper.sh

# Contenido del archivo nano
sleep 5
x-terminal-emulator -e "/usr/bin/ghostwhisperchat"
#Control o + enter + control x

# Darle permisos
chmod +x ~/autostart_ghostwhisper.sh

# Habilitar autostart
mkdir -p ~/.config/autostart
nano ~/.config/autostart/ghostwhisper.desktop

# Contenido segundo nano
[Desktop Entry]
Type=Application
Name=GhostWhisperChat Terminal
Exec=/home/kali/autostart_ghostwhisper.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true






