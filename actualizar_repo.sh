#!/bin/bash
# Script Maestro de Publicación GhostWhisperChat
# Autor: CyberDEI Team
# Uso: ./actualizar_repo.sh

set -e

# Configuración
REPO_ROOT=$(pwd)
SOURCE="$HOME/Escritorio/inter_chat.py"
PKG_DIR="ghostwhisperchat_pkg"
BIN_DEST="$PKG_DIR/usr/bin/ghostwhisperchat"
DEB_NAME="ghostwhisperchat_33.0_all.deb" # Asegurarse que coincida con control
POOL_DIR="pool/main/g/ghostwhisperchat"
DISTS_DIR="dists/stable/main"

echo "=== GhostWhisperChat Repo Builder v2 ==="

# 1. Preparar Binario
echo "[1/6] Actualizando binario fuente..."
cp "$SOURCE" "$BIN_DEST"
chmod +x "$BIN_DEST"

# 2. Construir .DEB
echo "[2/6] Construyendo paquete Debian..."
chmod 755 "$PKG_DIR/DEBIAN"
chmod 755 "$PKG_DIR/DEBIAN/control"
dpkg-deb --build "$PKG_DIR" "$DEB_NAME"

# 3. Estructura de Repositorio
echo "[3/6] Organizando estructura de directorios..."
rm -rf dists pool # Limpieza radical para evitar corrupción
mkdir -p "$POOL_DIR"
mkdir -p "$DISTS_DIR/binary-amd64"
mkdir -p "$DISTS_DIR/binary-i386"
mkdir -p "$DISTS_DIR/binary-arm64"
mkdir -p "$DISTS_DIR/binary-all"

# 4. Mover Paquete
echo "[4/6] Archivando paquete en Pool..."
mv "$DEB_NAME" "$POOL_DIR/"

# 5. Generar Índices (Packages)
echo "[5/6] Analizando paquetes..."
# dpkg-scanpackages busca DEBs desde la raiz y genera rutas relativas
# binary-amd64
dpkg-scanpackages . /dev/null > "$DISTS_DIR/binary-amd64/Packages"
gzip -k -f "$DISTS_DIR/binary-amd64/Packages"

# binary-i386 (vacío pero necesario para que apt no tire 404 error)
touch "$DISTS_DIR/binary-i386/Packages"
gzip -k -f "$DISTS_DIR/binary-i386/Packages"

# binary-all (copia de amd64 pues es arquitectura 'all')
cp "$DISTS_DIR/binary-amd64/Packages" "$DISTS_DIR/binary-all/Packages"
gzip -k -f "$DISTS_DIR/binary-all/Packages"

# binary-arm64 (copia de amd64 pues es arquitectura 'all')
cp "$DISTS_DIR/binary-amd64/Packages" "$DISTS_DIR/binary-arm64/Packages"
gzip -k -f "$DISTS_DIR/binary-arm64/Packages"

# 6. Generar Release File (Vital para que apt acepte el repo)
echo "[6/6] Generando archivo Release..."
cat <<EOF > dists/stable/Release
Origin: GhostWhisperChat Repo
Label: GhostWhisperChat
Suite: stable
Codename: stable
Architectures: amd64 i386 arm64 all
Components: main
Description: Repositorio oficial de GhostWhisperChat
EOF

echo "========================================"
echo "[✔] Repositorio Reconstruido Exitosamente"
echo "========================================"
echo "Siguientes pasos:"
echo "1. git add ."
echo "2. git commit -m 'Repo refresh v33.0'"
echo "3. git push"
echo "========================================"
