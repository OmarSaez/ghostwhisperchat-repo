#!/bin/bash
echo "Modo vigilancia activado. Editando código..."

while true; do
    # Espera a que modifiques version.txt (así controlas cuándo lanzar la update)
    inotifywait -e close_write ./version.txt

    echo "Detectado cambio de versión. Reconstruyendo repositorio..."
    ./actualizar_repo.sh

    # Opcional: Si tienes el repo en GitHub Pages, sube los cambios solo
    # git add . && git commit -m "Auto update repo" && git push

    echo "Esperando próximos cambios..."
done
