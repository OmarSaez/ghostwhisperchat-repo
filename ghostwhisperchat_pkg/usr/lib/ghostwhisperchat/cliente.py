# /usr/lib/ghostwhisperchat/cliente.py
# Interfaz de Usuario (CLI) - Refactor v2.1
# Modo Transitorio (Comandos) + Modo UI (Ventana Dedicada)

import socket
import os
import sys
import threading
import time
import readline # Habilita historial con flechas automaticamente
import shutil
import argparse
from ghostwhisperchat.datos.recursos import Colores as C, BANNER

IPC_SOCK_PATH = os.path.expanduser("~/.ghostwhisperchat/gwc.sock")

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
    Modo Persistente: UI de Chat Dedicada.
    """
    mi_ip = get_local_ip()
    print(C.GREEN + BANNER + C.RESET)
    print(f"{C.BOLD}[*] IP LOCAL: {mi_ip} | CHAT CON: {target_id}{C.RESET}")
    print(f"{C.GREY}(Escribe y presiona Enter. Ctrl+C para cerrar){C.RESET}\n")
    
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

    # 2. Thread de Lectura (Incoming Messages)
    def escuchar():
        while True:
            try:
                data = s.recv(4096)
                if not data:
                    print(f"\n{C.RED}[!] Desconectado.{C.RESET}")
                    os._exit(0)
                
                # Input Protection Hack:
                # Borramos linea actual, imprimimos msg, y repintamos prompt
                # Nota: Esto es imperfecto sin curses, pero mejor que nada.
                # \r = return to start line, \033[K = clear line
                
                msg_in = data.decode('utf-8')
                
                # Check for special Close Trigger
                if "__CLOSE_UI__" in msg_in:
                    # Daemon is telling us to close.
                    # It likely sent [SISTEMA] xxx closed session before this.
                    # Wait 2 seconds as requested, then exit.
                    time.sleep(2.0)
                    os._exit(0)

                # Si es un eco nuestro (empieza con Tu:), asumimos que el input local ya lo mostró?
                # NO, decidimos que el daemon hace eco. Asi que borramos input local.
                
                sys.stdout.write(f"\r\033[K{msg_in}\n")
                sys.stdout.write("Tu: ") # Prompt
                sys.stdout.flush()
                
            except:
                break
        os._exit(0)
        
    t = threading.Thread(target=escuchar, daemon=True)
    t.start()
    
    # 3. Loop de Escritura (User Input)
    sys.stdout.write("Tu: ")
    sys.stdout.flush()
    
    while True:
        try:
            # readline ya maneja el historial con flechas
            msg = input() 
            
            # Al dar enter, readline deja el texto ahi.
            # Nosotros mandamos al daemon, que nos hará eco con "Tu: lo que escribi"
            # ENTONCES: Para que no salga duplicado "Tu: hola" (local) y "Tu: hola" (red),
            # deberiamos borrar la linea local o confiar en el eco.
            # V2.27: Confiamos en el ECO del daemon.
            # Borramos la linea que acabamos de escribir para que el eco la reemplace limpiamente
            sys.stdout.write("\033[A\033[K") # Subir una linea y borrarla
            
            if msg.strip():
                if msg.startswith("--") or msg.startswith("/"):
                    # Comandos no llevan prefijo "Tu:" en el servidor, 
                    # pero el resultado [SISTEMA] se imprimirá.
                    pass
                
                payload = f"__MSG__ {msg}"
                s.sendall(payload.encode('utf-8'))
                
        except KeyboardInterrupt:
            print("\nCerrando chat...")
            break
        except EOFError:
            break
            
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
        enviar_comando_transitorio(full_cmd)

if __name__ == "__main__":
    main()
