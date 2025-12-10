#!/bin/bash
# actualizar_repo.sh (VERSIÓN FINAL PRO)
# Script para construir, limpiar y actualizar el repositorio

set -e

# --- 1. CONFIGURACIÓN ---
REPO_DIR="$(pwd)"
SOURCE_PKG_DIR="$REPO_DIR/ghostwhisperchat_pkg"
POOL_DIR="$REPO_DIR/pool/main/g/ghostwhisperchat"
DIST_DIR="$REPO_DIR/dists/stable"
ARCHS=("amd64" "all" "arm64" "i386")
PACKAGE_NAME="ghostwhisperchat"

# --- 2. OBTENER VERSIÓN ---
if [ ! -f "$REPO_DIR/version.txt" ]; then
    echo "❌ Error: No encuentro el archivo version.txt"
    exit 1
fi

VERSION=$(cat "$REPO_DIR/version.txt")
echo "=========================================="
echo "🚀 INICIANDO ACTUALIZACIÓN A VERSIÓN: $VERSION"
echo "=========================================="

# --- 3. ACTUALIZAR ARCHIVO CONTROL ---
CONTROL_FILE="$SOURCE_PKG_DIR/DEBIAN/control"
if [ -f "$CONTROL_FILE" ]; then
    sed -i "s/^Version: .*/Version: $VERSION/" "$CONTROL_FILE"
    echo "✅ Archivo control actualizado a versión $VERSION"
else
    echo "❌ Error: No encuentro DEBIAN/control"
    exit 1
fi

# --- 4. CONSTRUIR EL PAQUETE .DEB ---
DEB_FILENAME="${PACKAGE_NAME}_${VERSION}_all.deb"
echo "🔨 Construyendo paquete $DEB_FILENAME..."

# --root-owner-group: Arregla la advertencia de permisos inusuales
dpkg-deb --root-owner-group --build "$SOURCE_PKG_DIR" "$DEB_FILENAME"

mkdir -p "$POOL_DIR"
mv "$DEB_FILENAME" "$POOL_DIR/"
echo "📦 Paquete movido a: $POOL_DIR/$DEB_FILENAME"

# --- 5. LIMPIEZA AUTOMÁTICA (Mantiene las 3 últimas versiones) ---
echo "🧹 Limpiando versiones antiguas..."
cd "$POOL_DIR"
# Cuenta cuantos .deb hay, si hay mas de 3, borra los viejos
ls -t ${PACKAGE_NAME}_*.deb | tail -n +4 | xargs -I {} rm -- {} 2>/dev/null || true
cd "$REPO_DIR"

# --- 6. ACTUALIZAR ÍNDICES (Packages.gz) ---
# ESTO ES LO QUE ACTUALIZA EL "CATÁLOGO" PARA APT
echo "🔄 Regenerando catálogo (Packages.gz)..."
for ARCH in "${ARCHS[@]}"; do
    TARGET_DIR="$DIST_DIR/main/binary-$ARCH"
    mkdir -p "$TARGET_DIR"
    # Escaneamos desde '.' para usar rutas relativas
    dpkg-scanpackages -m . /dev/null | gzip -9c > "$TARGET_DIR/Packages.gz"
done

# --- 7. GENERAR RELEASE (Hashes de seguridad) ---
echo "📝 Generando firmas Release..."
cd "$DIST_DIR"
cat > Release <<EOF
Origin: GhostWhisperChat Repo
Label: GhostWhisperChat
Suite: stable
Codename: stable
Version: 1.0
Architectures: amd64 all arm64 i386
Components: main
Description: Repositorio oficial de GhostWhisperChat
Date: $(date -R)
EOF

# Generar Hashes
echo "MD5Sum:" >> Release
find main -name "Packages.gz" | while read f; do echo " $(md5sum "$f" | awk '{print $1}') $(stat -c%s "$f") $f" >> Release; done
echo "SHA256:" >> Release
find main -name "Packages.gz" | while read f; do echo " $(sha256sum "$f" | awk '{print $1}') $(stat -c%s "$f") $f" >> Release; done

cd "$REPO_DIR"
echo "=========================================="
echo "✅ ¡ÉXITO! Repositorio listo (Versión $VERSION)"
echo "=========================================="
