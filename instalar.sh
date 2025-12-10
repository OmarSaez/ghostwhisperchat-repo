#!/bin/bash
# Script de instalación automática para Cliente
# Compatible con Kali, Ubuntu, Debian

echo "👻 Instalando GhostWhisperChat..."

# 1. Instalar dependencias básicas si faltan
sudo apt update
sudo apt install -y curl wget gpg

# 2. Agregar Clave GPG (Formato Moderno)
echo "🔑 Importando llave GPG..."
wget -qO - https://omarsaez.github.io/ghostwhisperchat-repo/public.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/ghostwhisperchat.gpg > /dev/null

# 3. Agregar Repositorio
echo "📂 Configurando repositorio..."
echo "deb https://omarsaez.github.io/ghostwhisperchat-repo/ stable main" | sudo tee /etc/apt/sources.list.d/ghostwhisperchat.list

# 4. Instalar Paquete
echo "⬇️  Descargando e instalando..."
sudo apt update
sudo apt install ghostwhisperchat -y

echo "✅ Instalación completada. Ejecuta 'ghostwhisperchat' para iniciar."
