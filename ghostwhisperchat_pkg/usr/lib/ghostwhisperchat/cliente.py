# /usr/lib/ghostwhisperchat/cliente.py
# Interfaz de Usuario (CLI) - Refactor v2.1
# Modo Transitorio (Comandos) + Modo UI (Ventana Dedicada)

import socket
import select
import os
import sys
import threading
import time
import termios # Raw mode input
import tty     # Raw mode utility
import shutil
import argparse
from ghostwhisperchat.datos.recursos import Colores as C, BANNER
from ghostwhisperchat.core import imagen_ascii # Modulo ASCII Art

IPC_SOCK_PATH = os.path.expanduser("~/.ghostwhisperchat/gwc.sock")

# --- CLASE GESTOR DE INPUT (Raw Mode) ---
class GestorInput:
    def __init__(self, socket_client):
        self.sock = socket_client
        self.buffer = []
        self.prompt = "Tu: "
        self.lock = threading.RLock() # RLock para evitar deadlock en llamadas anidadas
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
            
            # --- PROTOCOLO IMAGEN SEGURA (v2.150) ---
            if "[B64_IMG]" in msg:
                try:
                    # Formato: ... [B64_IMG]HEADER|PAYLOAD_B64 ... (Puede venir embedido en un chat con hora)
                    # El prefix [B64_IMG] marca el inicio de la zona segura.
                    # Asumimos que el mensaje entero ES la imagen si tiene el tag, 
                    # pero debemos conservar la parte "[Hora] (Nick): " que motor.py agrego al principio.
                    
                    parts = msg.split("[B64_IMG]")
                    prefix = parts[0] # "[12:00] (Nick): "
                    contact_content = parts[1] # "HEADER|B64"
                    
                    if "|" in contact_content:
                        header, b64_payload = contact_content.split("|", 1)
                        import base64
                        decoded_img = base64.b64decode(b64_payload).decode('utf-8', errors='replace')
                        
                        # Reconstruimos msg final
                        # Header tiene sus propios newlines
                        msg = f"{prefix}{header}{decoded_img}"
                    else:
                        msg = f"{prefix}[Error Protocolo img]"
                except Exception as e:
                    msg = f"[Error Decode Img: {e}]"

            # Decodificar newlines de ASCII Art Legacy (por si acaso queda alguno)
            msg = msg.replace("<<ASCII_NL>>", "\n")
            
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
                        # --- DETECCION INTELIGENTE DE PASTE (Bloques ASCII) ---
                        # Si hay más datos esperando inmediatamente en el stdin, es muy probable
                        # que sea un paste de texto multilínea. Agregamos \n en vez de enviar.
                        
                        is_paste = False
                        try:
                            # Peek no bloqueante (timeout aumentado a 30ms para terminales lentas)
                            rfds, _, _ = select.select([sys.stdin], [], [], 0.03)
                            if rfds:
                                is_paste = True
                        except:
                            pass
                            
                        if is_paste:
                            self.buffer.append('\n')
                            # Feedback visual mínimo: Salto de linea real + retorno carro
                            sys.stdout.write('\r\n')
                            sys.stdout.flush()
                        else:
                            # Enter manual -> Enviar mensaje acumulado
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
        file_to_send_bg = None # Para auto-envio de fotos
        
        try:
             # Check Scan
             from ghostwhisperchat.datos.recursos import COMMAND_MAP
             cmd_raw = msg.split()[0]
             if not cmd_raw.startswith("-"): cmd_raw = "--" + cmd_raw 
             
             # --- INTERCEPCION IMAGEN ASCII ---
             # Alias: --imagen, --foto, --picture, -P, -i
             IMG_ALIASES = ["--imagen", "--foto", "--picture", "-P", "-i"]
             if cmd_raw in IMG_ALIASES:
                 parts = msg.strip().split()
                 if len(parts) < 2:
                     self.print_incoming(f"{C.RED}[X] Uso: --imagen <ruta> [ancho]{C.RESET}")
                     return
                 
                 im_path = parts[1].strip("'").strip('"')
                 file_to_send_bg = im_path # Marcamos para envio background
                 
                 # Lógica de Ancho v2.155:
                 # 1. Default estricto: 60.
                 # 2. Si usuario define ancho: Se usa ese valor (Clampeado 10-190).
                 # Ya no hay auto-ajuste a la ventana local.
                 
                 im_width = 60 # Default
                 
                 if len(parts) > 2 and parts[2].isdigit():
                     user_val = int(parts[2])
                     im_width = max(10, min(user_val, 190))
                 
                 # Renderizar (Puede tardar unos ms)
                 self.print_incoming(f"{C.YELLOW}[*] Procesando imagen...{C.RESET}")
                 try:
                     res = imagen_ascii.render_ascii(im_path, im_width)
                 except Exception as e:
                     self.print_incoming(f"{C.RED}[X] Crash Rendering: {e}{C.RESET}")
                     return
                 
                 if res.startswith("ERROR:"):
                     self.print_incoming(f"{C.RED}[X] {res}{C.RESET}")
                     return
                 
                 
                 # Empaquetar con Protocolo Seguro Base64 (v2.150)
                 import base64
                 
                 # Header SAFE (Usamos <<ASCII_NL>> en vez de \n real para que viaje en 1 linea)
                 header_safe = f"<<ASCII_NL>>{C.CYAN}[IMAGEN ASCII] {os.path.basename(im_path)}{C.RESET}<<ASCII_NL>>"
                 
                 # Payload B64
                 full_content = res + C.RESET
                 b64_data = base64.b64encode(full_content.encode('utf-8')).decode('ascii')
                 
                 # Mensaje final: [B64_IMG] + HeaderSafe + | + B64
                 msg = f"[B64_IMG]{header_safe}|{b64_data}"
                 
                 # Actualizar cmd_raw
                 cmd_raw = "MSG_TEXT" 

             is_scan = cmd_raw in COMMAND_MAP['SCAN'] or cmd_raw in COMMAND_MAP['LIST_GROUPS']
             
             if is_scan:
                  # FIX v2.163: Protocolo Stream con \n tambien para comandos raw
                  self.sock.sendall(f"__MSG__ {msg}\n".encode('utf-8'))
                  sys.stdout.write("\r\n[*] Escaneando...\r\n")
                  # Anti-Coalescing Delay: Daemon needs time to read first msg (now less critical but kept for safety)
                  time.sleep(0.3) 
                  self.sock.sendall(b"__MSG__ --scan-results\n")
                  return

             payload = f"__MSG__ {msg}"
             
             # If command, inject display
             if msg.strip().startswith("--") and cmd_raw != "MSG_TEXT":
                 disp = os.environ.get('DISPLAY')
                 if disp: payload = f"{payload} __ENV_DISPLAY__={disp}"
                 
             # FIX v2.156: Append \n delimiter so Daemon can accumulate stream
             self.sock.sendall((payload + "\n").encode('utf-8'))
             
             # FIX v2.165: Dual-Send Background
             if file_to_send_bg:
                 time.sleep(0.5) # Aumentar pausa para asegurar que el ASCII termino de procesarse
                 # Construimos comando --file con RUTA ABSOLUTA para que el Daemon lo encuentre
                 abs_path = os.path.abspath(file_to_send_bg)
                 # FIX v2.166: Usar comando silencioso --foto-bg
                 cmd_file = f"__MSG__ --foto-bg \"{abs_path}\""
                 self.sock.sendall((cmd_file + "\n").encode('utf-8'))
                 # Feedback visual suprimido por el daemon (Modo Silencioso)

        except Exception as e:
             self.print_incoming(f"[ERROR CLI] {e}")

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
    print(f"{C.GREY}(Escribe --ayuda para ver comandos disponibles. Ctrl+C para cerrar){C.RESET}\n")
    
    # Init Input Helper
    helper = GestorInput(s)

    # 2. Thread de Lectura (Incoming Messages)
    def escuchar():
        buffer_bytes = b""
        while helper.running:
            try:
                # FIX v2.153: Buffer Acumulativo Real (Stream Handling)
                chunk = s.recv(262144) 
                if not chunk:
                    helper.running = False
                    break
                
                buffer_bytes += chunk
                
                # Procesar mensajes completos (terminados en \n)
                while b'\n' in buffer_bytes:
                    line_bytes, buffer_bytes = buffer_bytes.split(b'\n', 1)
                    if not line_bytes: continue
                    
                    line = ""
                    try:
                        line = line_bytes.decode('utf-8').strip()
                    except Exception as e:
                        helper.print_incoming(f"[ERROR RX] {e}")
                        continue

                    if not line: continue
                    
                    # Check for special Close Trigger
                    if "__CLOSE_UI__" in line:
                         helper.running = False
                         break

                    # FILTER: Hide ID confirmation message
                    if "Conectado al Daemon. ID:" in line:
                        continue

                    # --- SISTEMA COLORING (UX/UI Standard) ---
                    if line.startswith("[SISTEMA]"):
                        if "[X]" in line or "Error" in line:
                             line = f"{C.RED}{line}{C.RESET}"
                        elif "[-]" in line or "[!]" in line:
                             line = f"{C.YELLOW}{line}{C.RESET}"
                        else:
                             line = f"{C.GREEN}{line}{C.RESET}"
                    
                    # HIGHLIGHT: MENTION
                    if "__MENTION__" in line:
                        line = line.replace("__MENTION__ ", "")
                        # FIX v2.164: Reemplazar Resets internos para mantener el fondo amarillo
                        # Si hay un reset en medio (despues del nick), volvemos a aplicar el fondo.
                        line = line.replace(C.RESET, C.RESET + C.BG_YELLOW + C.BLACK_TXT)
                        # Aplicar estilo global
                        line = f"{C.BG_YELLOW}{C.BLACK_TXT}{line}{C.RESET}"
                        
                    # Use Helper to print safely
                    helper.print_incoming(line)
                    
                    # DEBUG: Trace painting (Append to file for validation)
                    try:
                        with open("/tmp/gwc_client_debug.txt", "a") as f:
                            # Strip ansi colors for readability in log
                            raw_line = line.replace('\x1b', '').replace('[', '').replace(']', '') 
                            f.write(f"[DEBUG_PAINT] Se pinto linea: {raw_line[:30]}...\n")
                    except: pass
                
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
