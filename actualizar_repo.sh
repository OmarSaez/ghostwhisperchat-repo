#!/bin/bash
# actualizar_repo.sh (VERSIÓN FINAL PRO 2.0)
# Script para construir, firmar y organizar el repositorio APT
# Compatible con Debian, Ubuntu, Kali.

set -e # Detener si hay error
export LC_TIME=C

# --- 1. CONFIGURACIÓN ---
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_PKG_DIR="$REPO_DIR/ghostwhisperchat_pkg"
POOL_DIR="$REPO_DIR/pool/main/g/ghostwhisperchat"
DIST_ROOT="$REPO_DIR/dists/stable"
ARCHS=("amd64" "all" "arm64" "i386")
PACKAGE_NAME="ghostwhisperchat"
GPG_EMAIL="omar.saez@usach.cl" # Debe coincidir con tu llave GPG

# --- CHEQUEOS PREVIOS ---
if ! command -v dpkg-scanpackages &> /dev/null; then
    echo "❌ Error: dpkg-scanpackages no instalado. Ejecuta: sudo apt install dpkg-dev"
    exit 1
fi
if ! command -v gpg &> /dev/null; then
    echo "❌ Error: gpg no encontrado."
    exit 1
fi

# --- 2. OBTENER VERSIÓN ---
if [ ! -f "$REPO_DIR/version.txt" ]; then
    echo "❌ Error: Falta version.txt"
    exit 1
fi
VERSION=$(cat "$REPO_DIR/version.txt" | tr -d '[:space:]')
echo "=========================================="
echo "🚀 BUILDER GHOSTWHISPERCHAT v$VERSION"
echo "=========================================="

# --- 3. ACTUALIZAR CONTROL FILE ---
CONTROL_FILE="$SOURCE_PKG_DIR/DEBIAN/control"
if [ -f "$CONTROL_FILE" ]; then
    sed -i "s/^Version: .*/Version: $VERSION/" "$CONTROL_FILE"
    echo "✅ Control actualizado."
else
    echo "❌ Error: Falta DEBIAN/control"
    exit 1
fi

# --- 4. CONSTRUIR .DEB ---
DEB_FILENAME="${PACKAGE_NAME}_${VERSION}_all.deb"
echo "🔨 Construyendo paquete $DEB_FILENAME..."

# Permisos fix (Simplificado sin sudo)
# dpkg-deb --root-owner-group ya hace que dentro del deb sea root:root
dpkg-deb --root-owner-group --build "$SOURCE_PKG_DIR" "$DEB_FILENAME"

mkdir -p "$POOL_DIR"
mv "$DEB_FILENAME" "$POOL_DIR/"
echo "📦 Paquete en Pool."

# --- 5. LIMPIEZA VIEJOS ---
echo "🧹 Limpiando versiones viejas del Pool..."
cd "$POOL_DIR"
ls -t ${PACKAGE_NAME}_*.deb | tail -n +4 | xargs -I {} rm -- {} 2>/dev/null || true
cd "$REPO_DIR"

# --- 6. GENERAR PACKAGES (SCAN) ---
echo "🔄 Regenerando índices Packages..."
for ARCH in "${ARCHS[@]}"; do
    BINARY_DIR="$DIST_ROOT/main/binary-$ARCH"
    mkdir -p "$BINARY_DIR"
    
    # IMPORTANTE: Escaneamos pool/ con ruta RELATIVA desde la raíz del repo
    # dpkg-scanpackages -m pool/main ... > dists/.../Packages
    dpkg-scanpackages -m pool /dev/null > "$BINARY_DIR/Packages" 2>/dev/null
    cat "$BINARY_DIR/Packages" | gzip -9c > "$BINARY_DIR/Packages.gz"
done

# --- 7. GENERAR RELEASE ---
echo "📝 Generando Release..."
cd "$DIST_ROOT"
rm -f Release Release.gpg InRelease

cat > Release <<EOF
Origin: GhostWhisperChat
Label: GhostWhisperChat Repo
Suite: stable
Codename: stable
Version: $VERSION
Architectures: $(echo ${ARCHS[*]})
Components: main
Description: Official GhostWhisperChat Repository
Date: $(date -uR)
EOF

# Calcular Hashes (MD5, SHA256)
# Debemos hashear Packages y Packages.gz de cada arquitectura
DO_HASH() {
    HASH_NAME=$1
    CMD=$2
    echo "$HASH_NAME:" >> Release
    for ARCH in "${ARCHS[@]}"; do
        P="main/binary-$ARCH/Packages"
        PG="main/binary-$ARCH/Packages.gz"
        if [ -f "$P" ]; then
            echo " $($CMD "$P" | awk '{print $1}') $(stat -c%s "$P") $P" >> Release
        fi
        if [ -f "$PG" ]; then
            echo " $($CMD "$PG" | awk '{print $1}') $(stat -c%s "$PG") $PG" >> Release
        fi
    done
}

DO_HASH "MD5Sum" "md5sum"
DO_HASH "SHA256" "sha256sum"

# --- 8. FIRMAR CON GPG ---
echo "🔐 Firmando repositorio..."
# Usamos el email definido arriba.
# Si falla, es probable que no tengas la key privada importada.
gpg --batch --yes --detach-sign --armor --local-user "$GPG_EMAIL" --output Release.gpg Release
gpg --batch --yes --clearsign --local-user "$GPG_EMAIL" --output InRelease Release

cd "$REPO_DIR"
echo "=========================================="
echo "✅ REPOSITORIO LISTO Y FIRMADO"
echo "=========================================="
echo "Siguientes pasos:"
echo "1. git add ."
echo "2. git commit -m 'Repo v$VERSION signed'"
echo "3. git push"
