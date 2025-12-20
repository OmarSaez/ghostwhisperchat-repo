# /usr/lib/ghostwhisperchat/cliente.py
# Interfaz de Usuario (CLI) - Refactor v2.1
# Modo Transitorio (Comandos) + Modo UI (Ventana Dedicada)

import socket
import os
import sys
import threading
import time
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

def modo_ui_chat(target_id, es_grupo):
    """
    Modo Persistente: UI de Chat Dedicada.
    Se conecta al daemon y se suscribe a eventos de este chat específico.
    """
    print(C.GREEN + BANNER + C.RESET)
    print(f"{C.BOLD}[*] CHAT ACTIVO CON: {target_id}{C.RESET}")
    print(f"{C.GREY}(Escribe y presiona Enter para enviar. Ctrl+C para cerrar){C.RESET}\n")
    
    # 1. Conectar Persistente
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(IPC_SOCK_PATH)
        
        # Handshake de UI: Decirle al daemon "Soy UI para X"
        # Usamos un comando especial interno
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
                    break
                # Imprimir mensaje "crudo" que manda el Daemon ya formateado
                # O podríamos recibir JSON y formatear aquí. 
                # Por simplicidad v2.1, el Daemon manda texto formateado listo para imprimir.
                print(data.decode('utf-8'), end='') 
            except:
                break
        os._exit(0)
        
    t = threading.Thread(target=escuchar, daemon=True)
    t.start()
    
    # 3. Loop de Escritura (User Input)
    while True:
        try:
            msg = input() # Bloqueante
            # Borrar linea del input local para que no duplique visualmente si el daemon hace eco
            # O mejor: El input local se ve, y el daemon SOLO manda lo que viene de AFUERA.
            # Para chat visual limpio:
            # Opción A: Imprimo mi msg localmente 'Yo: ...' y mando al daemon.
            # Opción B: Mando al daemon y él me hace eco. (Mayor latencia visual, mejor consistencia).
            # Vamos por Opción A visual simple. 
            
            if msg.strip():
                # Enviar MSG al daemon
                # Formato comando interno UI: "__MSG__ <texto>"
                # El daemon sabe a quien va porque el socket esta registrado.
                payload = f"__MSG__ {msg}"
                s.sendall(payload.encode('utf-8'))
                
        except KeyboardInterrupt:
            print("\nCerrando chat...")
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
        # Modo Transitorio: Unir todos los args en un string y mandar
        # Ej: ['--dm', 'Pepe'] -> "--dm Pepe"
        # Cuidado con comillas, pero shlex en daemon lo manejará.
        # Mejor mandamos tal cual.
        full_cmd = " ".join(args_raw)
        enviar_comando_transitorio(full_cmd)

if __name__ == "__main__":
    main()
