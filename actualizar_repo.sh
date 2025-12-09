#!/bin/bash
# Script de Auto-Publicación GhostWhisperChat
# Ejecutar desde la carpeta del repositorio: ./actualizar_repo.sh

set -e

REPO_ROOT="/home/omar/Escritorio/ghostwhisperchat-repo"
SOURCE="/home/omar/Escritorio/inter_chat.py"
PKG_DIR="ghostwhisperchat_pkg"
BIN_DEST="$PKG_DIR/usr/bin/ghostwhisperchat"
DEB_NAME="ghostwhisperchat_32.8_all.deb"
POOL_DIR="pool/main/g"

echo "=== GhostWhisperChat Release Builder ==="

# 1. Actualizar Binario
echo "[1/5] Copiando fuente v32.8..."
cp "$SOURCE" "$BIN_DEST"
chmod +x "$BIN_DEST"

# 2. Construir Paquete
echo "[2/5] Construyendo .deb..."
dpkg-deb --build "$PKG_DIR" "$DEB_NAME"

# 3. Organizar en Pool
echo "[3/5] Moviendo a $POOL_DIR..."
# Limpiar versiones anteriores para evitar duplicados en índice si se desea
rm -f "$POOL_DIR"/ghostwhisperchat_*.deb
mv "$DEB_NAME" "$POOL_DIR/"

# 4. Generar Índices
echo "[4/5] Escaneando paquetes..."
# dpkg-scanpackages requiere estar en la raiz y apuntar a pool
dpkg-scanpackages pool/ > dists/stable/main/binary-amd64/Packages

# 5. Comprimir
echo "[5/5] Comprimiendo metadata..."
gzip -k -f dists/stable/main/binary-amd64/Packages > dists/stable/main/binary-amd64/Packages.gz

echo "========================================"
echo "[✔] Repositorio Actualizado a v32.8"
echo "Ahora ejecuta:"
echo "  git add ."
echo "  git commit -m 'Update v32.8'"
echo "  git push"
echo "========================================"
