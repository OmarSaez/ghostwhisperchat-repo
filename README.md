
# Chat LAN – GhostWhisperChat

Este es el desarrollo de un Chat LAN para uso interno de forma simple.

## INSTALADOR

```bash
echo "deb [trusted=yes] https://omarsaez.github.io/ghostwhisperchat-repo/ stable main" | sudo tee /etc/apt/sources.list.d/ghostwhisperchat.list

sudo apt update

sudo apt install ghostwhisperchat
```

## AUTOLEVANTADO

### 1. Crear Script de Inicio
```bash
nano ~/autostart_ghostwhisper.sh
```

Pegar este contenido:
```bash
#!/bin/bash
# Esperar a que el escritorio cargue
sleep 8

# Abrir GhostWhisperChat en terminal
x-terminal-emulator -e "/usr/bin/ghostwhisperchat"
```

Guardar: `Ctrl + O`, `Enter`, `Ctrl + X`

### 2. Dar Permisos de Ejecución
```bash
chmod +x ~/autostart_ghostwhisper.sh
```

### 3. Crear Archivo de Auto-inicio
```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/ghostwhisper.desktop
```

Pegar este contenido:
```ini
[Desktop Entry]
Type=Application
Name=GhostWhisperChat
Comment=Abre GhostWhisperChat al iniciar sesión
Exec=/home/USUARIO/autostart_ghostwhisper.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
```

### 4. Probar la Configuración
```bash
# Probar el script
~/autostart_ghostwhisper.sh

# Verificar que se crearon los archivos
ls -la ~/autostart_ghostwhisper.sh
ls -la ~/.config/autostart/ghostwhisper.desktop
```

### 5. Reiniciar para Verificar
```bash
sudo reboot
```
