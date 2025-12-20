# /usr/lib/ghostwhisperchat/demonio.py
# Punto de entrada del Servicio (Background)

import signal
import sys
import time
from ghostwhisperchat.logica.motor import Motor
from ghostwhisperchat.datos.config import cargar_config
from ghostwhisperchat.core.estado import MemoriaGlobal

def signal_handler(sig, frame):
    print("\n[!] Deteniendo Demonio...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    
    # 1. Cargar Configuración
    conf = cargar_config()
    
    # 2. Inicializar Memoria
    memoria = MemoriaGlobal()
    memoria.set_identidad(
        conf["user"]["uid"],
        conf["user"]["nick"],
        "127.0.0.1" # Se actualizará luego
    )
    memoria.no_molestar = conf["preferences"]["no_molestar"]
    
    # 3. Iniciar Motor
    try:
        motor = Motor()
        motor.bucle_principal()
    except Exception as e:
        import traceback
        print(f"[CRITICAL] Error fatal en demonio: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
