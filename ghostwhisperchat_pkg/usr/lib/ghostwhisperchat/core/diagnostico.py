# /usr/lib/ghostwhisperchat/core/diagnostico.py
# Módulo de Autodiagnóstico y Reporte Avanzado
import shutil
import socket
import os
import subprocess
import time
import sys
from ghostwhisperchat.datos.recursos import APP_VERSION, Colores as C

REQUIRED_DEPS = [("python3", "Motor Python"), ("zenity", "Interfaz de Ventanas"), ("notify-send", "Notificaciones"), ("fuser", "Gestor Procesos")]

def check_dependencies():
    print(f"\n{C.BOLD}:: Dependencias del Sistema ::{C.RESET}")
    all_ok = True
    for tool, desc in REQUIRED_DEPS:
        path = shutil.which(tool)
        if path:
            print(f" - {desc} ({tool}): {C.GREEN}OK{C.RESET}")
        else:
            print(f" - {desc} ({tool}): {C.RED}⚠️ FALTA{C.RESET}")
            all_ok = False
    return all_ok

def fetch_daemon_status():
    """Contacta al daemon para pedir sus puertos reales."""
    ipc_path = os.path.expanduser("~/.ghostwhisperchat/gwc.sock")
    if not os.path.exists(ipc_path): return None
    
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(ipc_path)
        s.sendall(b"--estatus") # GLOBAL_STATUS
        s.settimeout(2.0)
        data = s.recv(4096).decode('utf-8')
        s.close()
        return data
    except:
        return None

def parse_ports(status_text):
    """Extrae puertos TCP UDP del texto de estatus."""
    priv = 44494 # Default
    group = 44496 # Default
    pid = "UNK"
    
    if not status_text: return priv, group, pid
    
    for line in status_text.splitlines():
        if "Ports:" in line:
            # Ports: PRIV=XXXX GROUP=XXXX
            parts = line.split()
            for p in parts:
                if "PRIV=" in p: priv = int(p.split("=")[1])
                elif "GROUP=" in p: group = int(p.split("=")[1])
        elif "PID:" in line:
            pid = line.split(":")[1].strip()
            
    return priv, group, pid

def check_ports():
    print(f"\n{C.BOLD}:: Estado de Puertos (Daemon Health) ::{C.RESET}")
    
    # Intento de obtener puertos reales
    status = fetch_daemon_status()
    port_priv, port_group, pid = parse_ports(status)
    
    if status:
        print(f" -> Info del Demonio (PID {pid}): Detectado vivo via IPC.")
    else:
        print(f" -> {C.YELLOW}Demonio no responde via IPC. Verificando puertos default (Fallback)...{C.RESET}")

    # Verificar conectividad real
    ports = [
        (port_priv, "TCP Privado (Mensajes/Archivos)"),
        (44495, "UDP Discovery (Fijo)"),
        (port_group, "TCP Mesh (Grupos)")
    ]
    for p, desc in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            # Intentamos conectar. Si conecta (0), alguien escucha.
            res = s.connect_ex(('127.0.0.1', p))
            if res == 0:
                print(f" - Puerto {p} ({desc}): {C.GREEN}EN ESCUCHA (Activo){C.RESET}")
            else:
                # Si falla, puerto cerrado o filtrado
                print(f" - Puerto {p} ({desc}): {C.YELLOW}LIBRE / INACTIVO (Fallo){C.RESET}")

def check_ipc():
    print(f"\n{C.BOLD}:: Subsistema IPC (Socket Demonio) ::{C.RESET}")
    ipc_path = os.path.expanduser("~/.ghostwhisperchat/gwc.sock")
    if os.path.exists(ipc_path):
        # Intentar conectar
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(ipc_path)
            sock.close()
            print(f" - Socket {ipc_path}: {C.GREEN}OK (Conexión exitosa){C.RESET}")
        except Exception as e:
            print(f" - Socket {ipc_path}: {C.RED}FALLO (Existe pero no responde: {e}){C.RESET}")
            print(f"   {C.YELLOW}↳ Sugerencia: El daemon podría estar zombie.{C.RESET}")
    else:
        print(f" - Socket {ipc_path}: {C.RED}NO EXISTE (Daemon apagado){C.RESET}")

def check_filesystem():
    print(f"\n{C.BOLD}:: Sistema de Archivos ::{C.RESET}")
    conf_dir = os.path.expanduser("~/.ghostwhisperchat")
    if not os.path.exists(conf_dir):
        try:
            os.makedirs(conf_dir, mode=0o755)
            st_fs = f"{C.GREEN}OK (Creado){C.RESET}"
        except Exception as e:
            st_fs = f"{C.RED}ERROR ({e}){C.RESET}"
    elif os.access(conf_dir, os.W_OK):
        st_fs = f"{C.GREEN}OK (Escritura){C.RESET}"
    else:
        st_fs = f"{C.RED}FALLO (Permisos){C.RESET}"
    print(f" - Config (~/.ghostwhisperchat): {st_fs}")

def check_display():
    print(f"\n{C.BOLD}:: Entorno Gráfico & Terminales ::{C.RESET}")
    print(f"\n{C.BOLD}:: Entorno Gráfico & Terminales ::{C.RESET}")
    
    # 1. Variables de Entorno Críticas
    env_vars = ["DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"] # XDG_RUNTIME_DIR usually implicit
    print(f"Variables de Entorno (Contexto Shell):")
    
    display_ok = False
    
    for var in env_vars:
        val = os.environ.get(var)
        if val:
            print(f" - {var}: {C.GREEN}{val}{C.RESET}")
            if var == "DISPLAY": display_ok = True
        else:
            # Logic for criticality
            if var == "DISPLAY":
                print(f" - {var}: {C.RED}NO DETECTADO (Crítico para X11){C.RESET}")
            elif var == "DBUS_SESSION_BUS_ADDRESS":
                print(f" - {var}: {C.YELLOW}NO DETECTADO (Notificaciones pueden fallar){C.RESET}")
            else:
                print(f" - {var}: {C.GREY}No detectado (Opcional/Wayland){C.RESET}")

    if not display_ok:
        print(f"   {C.RED}↳ Las ventanas de chat NO se abrirán sin DISPLAY válido.{C.RESET}")

    # Verificar Terminales
    # Verificar Terminales
    from ghostwhisperchat.core.launcher import detectar_terminal, TERMINALES
    
    print(f"\nBusqueda de Terminales soportadas:")
    for t_name, _ in TERMINALES:
        res = f"{C.GREEN}INSTALADA{C.RESET}" if shutil.which(t_name) else f"{C.RED}NO ENCONTRADA{C.RESET}"
        print(f" - {t_name}: {res}")

    found_term, found_flag = detectar_terminal()

    if found_term:
        print(f" -> Se usará: {C.BOLD}{found_term}{C.RESET} (Flag: {found_flag})")
        # Test Live
        input_chk = input(f"\n¿Deseas probar lanzar una ventana real con {found_term}? (s/n): ")
        if input_chk.lower() == 's':
            try:
                cmd_inner = 'echo "GWC TEST EXITOSO"; echo "Cerrando en 5 segundos..."; sleep 5'
                
                cmd = [found_term]
                
                # Logic mirroring launcher.py
                if found_flag == "--":
                    # Gnome/Mate/XFCE
                    cmd.extend([found_flag, "sh", "-c", cmd_inner])
                elif found_flag == "-e" or found_flag == "-x":
                    # Wrapper for QTerminal/Konsole/etc
                    cmd.append(found_flag)
                    cmd.append(f"sh -c '{cmd_inner}'")
                
                print(f"   [DEBUG] Ejecutando: {cmd}")
                subprocess.Popen(cmd)
                print(f"   {C.GREEN}[INFO] Ventana lanzada. Si no se cierra en 5s, el comando falló.{C.RESET}")
            except Exception as e:
                print(f"   {C.RED}[ERROR] Falló lanzamiento: {e}{C.RESET}")
    else:
        print(f" -> {C.RED}ERROR: No se encontró ninguna terminal soportada.{C.RESET}")
        print(f"    Instala: gnome-terminal, qterminal, konsole, kitty o xterm.")

def ejecutar_diagnostico_completo():
    print(f"{C.BOLD}=== REPORTE DE INTEGRIDAD ({APP_VERSION}) ==={C.RESET}")
    check_dependencies()
    check_filesystem()
    check_ipc()
    check_ports()
    check_display()
    print("\n[FIN DEL DIAGNOSTICO]")

if __name__ == "__main__":
    ejecutar_diagnostico_completo()
