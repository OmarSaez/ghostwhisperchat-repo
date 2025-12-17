
# Chat LAN – GhostWhisperChat

Este es el desarrollo de un Chat LAN para uso interno de forma simple.

## INSTALADOR

```bash
# 1. Agregar Clave GPG
wget -qO - https://omarsaez.github.io/ghostwhisperchat-repo/public.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/ghostwhisperchat.gpg > /dev/null

# 2. Agregar Repositorio
echo "deb https://omarsaez.github.io/ghostwhisperchat-repo/ stable main" | sudo tee /etc/apt/sources.list.d/ghostwhisperchat.list

# 3. Instalar
sudo apt update
sudo apt install ghostwhisperchat
```
