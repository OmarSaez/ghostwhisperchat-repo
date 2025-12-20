# /usr/lib/ghostwhisperchat/core/diagnostico.py
# Módulo de Autodiagnóstico y Reporte

import shutil
import socket
import os
import subprocess
from ghostwhisperchat.datos.recursos import Colores as C

REQUIRED_HITS = ["zenity", "notify-send", "fuser"]

def check_dependencies():
    print(f"{C.BOLD}[*] Verificando dependencias del sistema...{C.RESET}")
    all_ok = True
    for tool in REQUIRED_HITS:
        path = shutil.which(tool)
        if path:
            print(f"  [OK] {tool}: {path}")
        else:
            print(f"  {C.RED}[X] {tool}: NO ENCONTRADO{C.RESET}")
            all_ok = False
            
    if not all_ok:
        print(f"{C.YELLOW}[!] Faltan dependencias. Instale: zenity libnotify-bin psmisc{C.RESET}")
    return all_ok

def check_ports():
    print(f"{C.BOLD}[*] Verificando puertos (44494-44496)...{C.RESET}")
    ports = [44494, 44495, 44496]
    busy = []
    
    for p in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        res = s.connect_ex(('127.0.0.1', p))
        s.close()
        # Si devuelve 0, es que conectó => ALGUIEN ESCUCHA (Puerto Ocupado)
        if res == 0:
            print(f"  {C.YELLOW}[!] Puerto {p} está en uso.{C.RESET}")
            busy.append(p)
        else:
            print(f"  [OK] Puerto {p} libre.")
            
    return busy

def check_filesystem():
    conf_dir = os.path.expanduser("~/.ghostwhisperchat")
    print(f"{C.BOLD}[*] Verificando permisos de escritura en {conf_dir}...{C.RESET}")
    
    if not os.path.exists(conf_dir):
        try:
            os.makedirs(conf_dir, mode=0o755)
            print("  [OK] Directorio creado.")
        except OSError as e:
            print(f"  {C.RED}[X] Error creando directorio: {e}{C.RESET}")
            return False
            
    if os.access(conf_dir, os.W_OK):
        print("  [OK] Escritura permitida.")
        return True
    else:
        print(f"  {C.RED}[X] Sin permisos de escritura.{C.RESET}")
        return False

def ejecutar_diagnostico_completo():
    print( "========================================")
    print(f" GHOSTWHISPERCHAT DIAGNOSTICO v2.0")
    print( "========================================")
    
    fs = check_filesystem()
    deps = check_dependencies()
    ports_busy = check_ports() # devuelve lista de ocupados
    
    print("\n--- CONCLUSIÓN ---")
    if not fs:
        print(f"{C.RED}[CRITICO] No se puede escribir configuración.{C.RESET}")
    elif not deps:
        print(f"{C.YELLOW}[ADVERTENCIA] Faltan herramientas visuales. El chat funcionará pero sin popups.{C.RESET}")
    
    if ports_busy:
        print(f"{C.BLUE}[INFO] Puertos ocupados: {ports_busy}. Si es GWC corriendo, todo bien.{C.RESET}")
    else:
        print(f"{C.GREEN}[INFO] Puertos libres. Listo para iniciar daemon.{C.RESET}")
        
if __name__ == "__main__":
    ejecutar_diagnostico_completo()
