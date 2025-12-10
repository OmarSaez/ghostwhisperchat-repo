#!/bin/bash
# actualizar_repo.sh
# Script para actualizar automáticamente el repositorio de GhostWhisperChat

set -e  # Salir si hay algún error

# Variables
REPO_DIR="$(pwd)"
POOL_DIR="$REPO_DIR/pool/main/g/ghostwhisperchat"
DIST_DIR="$REPO_DIR/dists/stable"
ARCHS=("amd64" "all" "arm64" "i386")  # Arquitecturas soportadas
PACKAGE_NAME="ghostwhisperchat"

echo "==> Actualizando paquete en el repositorio..."

# Copiar nuevo .deb a pool
LATEST_DEB=$(ls -1t $REPO_DIR/ghostwhisperchat_pkg/usr/bin/ghostwhisperchat* 2>/dev/null | head -n 1)
if [[ -z "$LATEST_DEB" ]]; then
    echo "No se encontró el paquete a actualizar. Verifica la ruta."
    exit 1
fi

# Para simplificar, asumimos que ya tienes el .deb listo en pool
# Si quieres, puedes generar el .deb automáticamente aquí también con dpkg-deb

echo "==> Generando Packages.gz para cada arquitectura..."
for ARCH in "${ARCHS[@]}"; do
    mkdir -p "$DIST_DIR/main/binary-$ARCH"
    dpkg-scanpackages "$POOL_DIR" /dev/null | gzip -9c > "$DIST_DIR/main/binary-$ARCH/Packages.gz"
done

echo "==> Generando Release..."
cat > "$DIST_DIR/Release" <<EOF
Origin: GhostWhisperChat Repo
Label: GhostWhisperChat
Suite: stable
Codename: stable
Architectures: amd64 all arm64 i386
Components: main
Description: Repositorio de GhostWhisperChat
EOF

# Calcular hashes automáticamente
echo "MD5Sum:" >> "$DIST_DIR/Release"
find "$DIST_DIR/main" -type f -name "Packages.gz" | while read f; do
    MD5=$(md5sum "$f" | awk '{print $1}')
    SIZE=$(stat -c%s "$f")
    echo " $MD5 $SIZE $(realpath --relative-to="$DIST_DIR" "$f")" >> "$DIST_DIR/Release"
done

echo "SHA1:" >> "$DIST_DIR/Release"
find "$DIST_DIR/main" -type f -name "Packages.gz" | while read f; do
    SHA1=$(sha1sum "$f" | awk '{print $1}')
    SIZE=$(stat -c%s "$f")
    echo " $SHA1 $SIZE $(realpath --relative-to="$DIST_DIR" "$f")" >> "$DIST_DIR/Release"
done

echo "SHA256:" >> "$DIST_DIR/Release"
find "$DIST_DIR/main" -type f -name "Packages.gz" | while read f; do
    SHA256=$(sha256sum "$f" | awk '{print $1}')
    SIZE=$(stat -c%s "$f")
    echo " $SHA256 $SIZE $(realpath --relative-to="$DIST_DIR" "$f")" >> "$DIST_DIR/Release"
done

echo "SHA512:" >> "$DIST_DIR/Release"
find "$DIST_DIR/main" -type f -name "Packages.gz" | while read f; do
    SHA512=$(sha512sum "$f" | awk '{print $1}')
    SIZE=$(stat -c%s "$f")
    echo " $SHA512 $SIZE $(realpath --relative-to="$DIST_DIR" "$f")" >> "$DIST_DIR/Release"
done

echo "==> Repositorio actualizado correctamente."
