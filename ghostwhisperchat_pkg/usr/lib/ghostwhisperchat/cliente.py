# /usr/lib/ghostwhisperchat/cliente.py
# Interfaz de Usuario (CLI) - Refactor v2.1
# Modo Transitorio (Comandos) + Modo UI (Ventana Dedicada)

import socket
import os
import sys
import threading
import time
import termios # Raw mode input
import tty     # Raw mode utility
import shutil
import argparse
from ghostwhisperchat.datos.recursos import Colores as C, BANNER

IPC_SOCK_PATH = os.path.expanduser("~/.ghostwhisperchat/gwc.sock")

# --- CLASE GESTOR DE INPUT (Raw Mode) ---
class GestorInput:
    def __init__(self, socket_client):
        self.sock = socket_client
        self.buffer = []
        self.prompt = "Tu: "
        self.lock = threading.Lock()
        self.running = True
        self.history = []
        self.history_index = 0
        
    def _limpiar_linea(self):
        # Mover al inicio, borrar linea completa
        sys.stdout.write("\r\033[K")
        
    def _pintar_linea(self):
        # Pintar prompt + buffer actual
        sys.stdout.write(f"{self.prompt}{''.join(self.buffer)}")
        sys.stdout.flush()

    def print_incoming(self, msg):
        """Imprime mensaje entrante sin romper el input actual"""
        with self.lock:
            self._limpiar_linea()
            # Asegurar retorno de carro para raw mode (\n -> \r\n)
            msg = msg.replace('\n', '\r\n')
            sys.stdout.write(f"{msg}\r\n") 
            self._pintar_linea()
            
    def input_loop(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            while self.running:
                ch = sys.stdin.read(1)
                
                with self.lock:
                    if ch == '\x03': # Ctrl+C
                        self.running = False
                        break
                        
                    elif ch == '\r' or ch == '\n': # Enter
                        linea = "".join(self.buffer)
                        self.buffer = [] # Limpiar buffer visualmente
                        self._limpiar_linea()
                        self._pintar_linea() # Queda "Tu: " vacio esperando eco o siguiente msg
                        
                        # Procesar comando (sin bloquear el lock mucho tiempo)
                        if linea.strip():
                             self.history.append(linea)
                             self.history_index = len(self.history)
                             self._enviar_mensaje(linea)
                             
                    elif ch == '\x7f' or ch == '\x08': # Backspace
                        if self.buffer:
                            self.buffer.pop()
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                        
                    elif ch == '\x1b': # Escape seq (Flechas)
                        # Leer siguientes 2
                        seq1 = sys.stdin.read(1)
                        seq2 = sys.stdin.read(1)
                        if seq1 == '[':
                            if seq2 == 'A': # Arriba
                                if self.history and self.history_index > 0:
                                    self.history_index -= 1
                                    self.buffer = list(self.history[self.history_index])
                                    self._limpiar_linea()
                                    self._pintar_linea()
                            elif seq2 == 'B': # Abajo
                                if self.history_index < len(self.history):
                                    self.history_index += 1
                                    if self.history_index == len(self.history):
                                        self.buffer = []
                                    else:
                                        self.buffer = list(self.history[self.history_index])
                                    self._limpiar_linea()
                                    self._pintar_linea()
                                    
                    else:
                        if ch.isprintable():
                            self.buffer.append(ch)
                            sys.stdout.write(ch)
                            sys.stdout.flush()
                            
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            print("\nCerrando interfaz...")

    def _enviar_mensaje(self, msg):
        # Logica original de envio
        try:
             # Check Scan
             from ghostwhisperchat.datos.recursos import COMMAND_MAP
             cmd_raw = msg.split()[0]
             if not cmd_raw.startswith("-"): cmd_raw = "--" + cmd_raw 
             is_scan = cmd_raw in COMMAND_MAP['SCAN'] or cmd_raw in COMMAND_MAP['LIST_GROUPS']
             
             if is_scan:
                  self.sock.sendall(f"__MSG__ {msg}".encode('utf-8'))
                  sys.stdout.write("\r\n[*] Escaneando...\r\n")
                  # Anti-Coalescing Delay: Daemon needs time to read first msg
                  time.sleep(0.3) 
                  self.sock.sendall(b"__MSG__ --scan-results")
                  return

             payload = f"__MSG__ {msg}"
             
             # If command, inject display
             if msg.strip().startswith("--"):
                 disp = os.environ.get('DISPLAY')
                 if disp: payload = f"{payload} __ENV_DISPLAY__={disp}"
                 
             self.sock.sendall(payload.encode('utf-8'))
        except:
             pass

def enviar_comando_transitorio(cmd_str):
    """Envía un comando, espera respuesta inmediata y sale."""
    if not os.path.exists(IPC_SOCK_PATH):
        print(f"{C.RED}[X] El servicio ghostwhisperchat no está corriendo.{C.RESET}")
        return

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(IPC_SOCK_PATH)
        s.sendall(cmd_str.encode('utf-8'))
        
        # Esperar ACK o Respuesta breve (Timeout corto)
        s.settimeout(2.0)
        try:
            resp = s.recv(4096)
            if resp:
                print(resp.decode('utf-8').strip())
        except socket.timeout:
            pass # Si no hay respuesta rapida, asumimos que fue procesado
            
        s.close()
    except Exception as e:
        print(f"{C.RED}[X] Error comunicando con daemon: {e}{C.RESET}")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def modo_ui_chat(target_id, es_grupo):
    """
    Modo Persistente: UI de Chat Dedicada (Raw Mode v2.1)
    """
    mi_ip = get_local_ip()
    print(C.GREEN + BANNER + C.RESET)
    
    # 1. Conectar Persistente
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(IPC_SOCK_PATH)
        
        tipo = "GROUP" if es_grupo else "PRIVATE"
        handshake = f"__REGISTER_UI__ {tipo} {target_id}"
        s.sendall(handshake.encode('utf-8'))
        
    except Exception as e:
        print(f"{C.RED}[X] Fallo conexión UI: {e}{C.RESET}")
        input("Presiona Enter para cerrar...")
        return
        
    # Header Limpio (Sin IDs)
    print(f"{C.BOLD}[*] IP LOCAL: {mi_ip}{C.RESET}")
    print(f"{C.GREY}(Escribe y presiona Enter. Ctrl+C para cerrar){C.RESET}\n")
    
    # Init Input Helper
    helper = GestorInput(s)

    # 2. Thread de Lectura (Incoming Messages)
    def escuchar():
        while helper.running:
            try:
                data = s.recv(4096)
                if not data:
                    helper.running = False
                    # Raw mode makes printing hard here, relying on main loop break
                    break
                
                msg_in = data.decode('utf-8')
                
                # Check for special Close Trigger
                if "__CLOSE_UI__" in msg_in:
                    helper.running = False
                    break

                # FIX SPACING: Strip trailing newlines from message itself
                msg_in = msg_in.strip()
                if not msg_in: continue
                
                # --- SISTEMA COLORING (UX/UI Standard) ---
                if msg_in.startswith("[SISTEMA]"):
                    if "[X]" in msg_in or "Error" in msg_in:
                         msg_in = f"{C.RED}{msg_in}{C.RESET}"
                    elif "[-]" in msg_in or "[!]" in msg_in:
                         msg_in = f"{C.YELLOW}{msg_in}{C.RESET}"
                    else:
                         msg_in = f"{C.GREEN}{msg_in}{C.RESET}"
                
                # FILTER: Hide ID confirmation message
                if "Conectado al Daemon. ID:" in msg_in:
                    continue

                # HIGHLIGHT: MENTION
                if "__MENTION__" in msg_in:
                    msg_in = msg_in.replace("__MENTION__ ", "")
                    # Yellow Background, Black Text for high contrast
                    msg_in = f"{C.BG_YELLOW}{C.BLACK_TXT}{msg_in}{C.RESET}"
                    
                # Use Helper to print safely
                helper.print_incoming(msg_in)
                
            except:
                break
        
        helper.running = False
        os._exit(0) # Force exit to kill raw mode loop
        
    t = threading.Thread(target=escuchar, daemon=True)
    t.start()
    
    # 3. Loop de Escritura (Raw Input via Helper)
    # Print initial prompt
    sys.stdout.write("Tu: ")
    sys.stdout.flush()
    
    # Run loop
    helper.input_loop()
    
    s.close()
    
def main():
    parser = argparse.ArgumentParser(add_help=False) # Parseo manual parcial
    parser.add_argument("--chat-ui", action="store")
    parser.add_argument("--group", action="store_true")
    
    # Truco: Si hay argumentos desconocidos, es un comando transitorio normal (ej: --dm, --salir)
    # Si tenemos --chat-ui, entramos en modo UI.
    
    # Primero miramos sys.argv tal cual
    args_raw = sys.argv[1:]
    
    if not args_raw:
        # Modo 'Shell' interactivo legado o ayuda?
        # En v2.1 si corres 'gwc' a secas, mostramos ayuda y salimos, o prompt simple.
        # User pidio: "comandos deberian funcionar en cualquier consola con gwc"
        print(f"{C.BOLD}GhostWhisperChat v2{C.RESET}")
        print("Uso: gwc <comando> [argumentos]")
        print("Ejemplo: gwc --dm Kali114 ; para mandar una solicitud de chat privado")
        print("Escribe: gwc --ayuda para ver lista completa.")
        print("Escribe: gwc --abrevaciones para ver lista de abrevaciones de los comandos")
        return

    # Detectar flag UI
    if "--chat-ui" in args_raw:
        # Parsear bien
        known, unknown = parser.parse_known_args()
        modo_ui_chat(known.chat_ui, known.group)
    elif "--version" in args_raw or "version" in args_raw:
        from ghostwhisperchat.datos.recursos import APP_VERSION
        print(f"GhostWhisperChat {APP_VERSION}")
    else:
        # Modo Transitorio
        from ghostwhisperchat.datos.recursos import COMMAND_MAP
        
        # 1. Normalización de Comandos (Auto-prefix)
        # Si el usuario escribe "gwc info" -> convertimos a "--info"
        cmd = args_raw[0]
        if not cmd.startswith("-"):
            args_raw[0] = "--" + cmd
            
        full_cmd = " ".join(args_raw)
        
        # 2. Lógica Especial para Escaneo (UX)
        # Check all aliases for SCAN and LIST_GROUPS
        if args_raw[0] in COMMAND_MAP['SCAN'] or args_raw[0] in COMMAND_MAP['LIST_GROUPS']:
            # Paso A: Disparar el Scan UDP (ya sea --scan o --vergrupos)
            enviar_comando_transitorio(full_cmd) # enviamos el comando original
            
            # Paso B: Animación de Espera (1.2s)
            from ghostwhisperchat.datos.recursos import mostrar_animacion_espera
            msg_anim = "Escaneando red" if args_raw[0] in COMMAND_MAP['SCAN'] else "Buscando grupos"
            mostrar_animacion_espera(msg_anim, 1.2)
            
            # Paso C: Pedir resultados
            # El daemon ya habrá poblado self.memoria.peers
            enviar_comando_transitorio("--scan-results")
            return

        # 3. Comando Normal
        # Inject Universal Environment Context
        injection = ""
        
        disp = os.environ.get('DISPLAY')
        if disp: injection += f" __ENV_DISPLAY__={disp}"
        
        way = os.environ.get('WAYLAND_DISPLAY')
        if way: injection += f" __ENV_WAYLAND__={way}"
        
        dbus = os.environ.get('DBUS_SESSION_BUS_ADDRESS')
        if dbus: injection += f" __ENV_DBUS__={dbus}"
        
        full_cmd += injection
        
        enviar_comando_transitorio(full_cmd)

if __name__ == "__main__":
    main()
