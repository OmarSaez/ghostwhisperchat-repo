# /usr/lib/ghostwhisperchat/logica/motor.py
# Motor Principal (Event Loop) - Refactor v2.1

import select
import socket
import os
import time
import sys
import threading
from ghostwhisperchat.core.estado import MemoriaGlobal
from ghostwhisperchat.core.transporte import GestorRed
from ghostwhisperchat.core.protocolo import empaquetar, desempaquetar
from ghostwhisperchat.core.launcher import abrir_chat_ui
from ghostwhisperchat.logica.comandos import parsear_comando, obtener_ayuda_comando
from ghostwhisperchat.datos.recursos import AYUDA, ABBREVIATIONS_DISPLAY
from ghostwhisperchat.logica import grupos
from ghostwhisperchat.logica.notificaciones import enviar_notificacion, preguntar_invitacion_chat

IPC_SOCK_PATH = os.path.expanduser("~/.ghostwhisperchat/gwc.sock")

class Motor:
    def __init__(self):
        self.memoria = MemoriaGlobal()
        self.red = GestorRed()
        self.ipc_sock = None
        self.running = False
        
        # Mapeo de UI Sockets: { "ID_CHAT": socket_ipc }
        # Esto permite enrutar mensajes al proceso de UI correcto
        self.ui_sessions = {} 

    def iniciar_ipc(self):
        if os.path.exists(IPC_SOCK_PATH):
            try:
                os.unlink(IPC_SOCK_PATH)
            except OSError:
                pass
        
        self.ipc_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.ipc_sock.bind(IPC_SOCK_PATH)
        self.ipc_sock.listen(5) # Aceptamos varias conexiones simultaneas (transitorias + UIs)
        self.ipc_sock.setblocking(False)

    def bucle_principal(self):
        """Loop principal del Demonio"""
        print("[*] Iniciando Motor GWC v2.1...", file=sys.stderr)
        
        if not self.red.iniciar_servidores():
            print("[X] Fallo en red. Abortando.", file=sys.stderr)
            return

        self.iniciar_ipc()
        self.running = True
        
        # Start PING thread
        threading.Thread(target=self._hilo_ping, daemon=True).start()
        
        print(f"[MOTOR_DEBUG] Entrando a Bucle Principal. Running={self.running}", file=sys.stderr)
        # ... (rest of loop code remains typical, updating select logic below if needed) ...
        try:
            while self.running:
                sockets_red = self.red.get_sockets_lectura()
                sockets_ui = list(self.ui_sessions.values())
                rlist = sockets_red + [self.ipc_sock] + sockets_ui
                
                try:
                    readable, _, _ = select.select(rlist, [], [], 2.0) # Faster tick for maintenance
                except select.error as e:
                    if e.args[0] == 4: continue
                    raise e
                    
                for s in readable:
                    if s == self.ipc_sock:
                        try:
                            conn, _ = s.accept()
                            conn.setblocking(True) 
                            data = conn.recv(4096)
                            if data:
                                self.procesar_ipc_mensaje(data.decode('utf-8').strip(), conn)
                            else:
                                conn.close()
                        except: pass
                    
                    elif s in sockets_ui:
                        try:
                            data = s.recv(4096)
                            if data: self.procesar_input_chat_ui(s, data.decode('utf-8'))
                            else: self.desconectar_ui(s)
                        except: self.desconectar_ui(s)
    
                    elif s == self.red.sock_udp:
                        try:
                            data, addr = s.recvfrom(65535)
                            self.manejar_paquete_udp(data, addr)
                        except Exception as e:
                           print(f"[UDP_ERR] {e}", file=sys.stderr)

                    elif s == self.red.sock_tcp_group or s == self.red.sock_tcp_priv:
                         self.red.aceptar_conexion(s) 

                    else: 
                        try:
                            data = s.recv(8192)
                            if data:
                                parts = data.split(b'\n')
                                for p in parts:
                                    if p: self.manejar_paquete_tcp(p, s)
                        except: self.red.cerrar_tcp(s)

                self.tareas_mantenimiento()

        except Exception as e:
             print(f"[CRASH] {e}", file=sys.stderr)
        finally:
             self.running = False

    def procesar_ipc_mensaje(self, mensaje, conn):
        """
        Maneja tanto comandos transitorios ("--dm ...") 
        como registros de UI ("__REGISTER_UI__ ...")
        """
        if mensaje.startswith("__REGISTER_UI__"):
            # Retro-compatibilidad con cliente.py existente
            partes = mensaje.split(" ", 2)
            if len(partes) >= 3:
                chat_id = partes[2]
                self.ui_sessions[chat_id] = conn
                print(f"[UI] Registrada ventana para {chat_id}", file=sys.stderr)
                conn.sendall(f"[*] Conectado al Daemon. ID: {chat_id}\n".encode('utf-8'))
            return

        elif mensaje.startswith("REGISTER_UI"):
            # Nuevo formato (por si acaso)
            parts = mensaje.split(":", 1)
            if len(parts) == 2:
                chat_id = parts[1]
                self.ui_sessions[chat_id] = conn
                print(f"[IPC] UI registrada para chat_id: {chat_id}", file=sys.stderr)
            return

        elif mensaje.startswith("--"):
            # Es un comando transitorio normal
            respuesta = self.ejecutar_comando_transitorio(mensaje)
            conn.sendall(respuesta.encode('utf-8'))
            conn.close()
        else:
            print(f"[IPC] Mensaje desconocido o MSG directo: {mensaje}", file=sys.stderr)
            conn.close()

    def ejecutar_comando_transitorio(self, comando_str, context_ui=None):
        print(f"[MOTOR_DEBUG] Procesando comando raw: {comando_str}", file=sys.stderr)
        cmd, args = parsear_comando(comando_str)
        
        if cmd == "HELP":
            return obtener_ayuda_comando(args[0] if args else None)

        elif cmd == "DM": 
             if not args: return "[X] Uso: --dm <Usuario>"
             target = args[0]
             
             # 1. Search in Peers (Nick or UID)
             peer = self.memoria.buscar_peer(target)
             if not peer:
                 # Try partial match or IP direct?
                 # Fail for now
                 return f"[X] Usuario '{target}' no encontrado en caché. Usa --enlinea primero."
             
             # 2. Send CHAT_REQ
             print(f"[WHISPER] Solicitando chat privado a {peer['nick']} ({peer['ip']})...", file=sys.stderr)
             pkg = empaquetar("CHAT_REQ", {}, self.memoria.get_origen())
             try:
                 self.red.enviar_tcp_priv(peer['ip'], pkg) # Uses Port 44494
                 return f"[*] Solicitud enviada a {peer['nick']}. Esperando respuesta..."
             except Exception as e:
                 return f"[X] Fallo al enviar solicitud: {e}"

    # ... (other commands) ...

    def manejar_paquete_tcp(self, data_bytes, sock):
        valid, data = desempaquetar(data_bytes)
        if not valid: return
        
        tipo = data.get("tipo")
        payload = data.get("payload")
        origen = data.get("origen")
        
        if origen:
             self.memoria.actualizar_peer(origen['ip'], origen['uid'], origen['nick'])

        # --- GROUP LOGIC ---
        if tipo == "JOIN_REQ":
            gid = payload.get("gid")
            if gid in self.memoria.grupos_activos:
                g = self.memoria.grupos_activos[gid]
                print(f"[MESH] Aceptando a {origen['nick']} en {g['nombre']}", file=sys.stderr)
                welcome = empaquetar("WELCOME", {"gid": gid, "name": g['nombre']}, self.memoria.get_origen())
                try: sock.sendall(welcome)
                except: pass
        
        elif tipo == "WELCOME":
             gid = payload.get("gid")
             name = payload.get("name")
             print(f"[MESH] ¡Acceso concedido a {name}!", file=sys.stderr)
             self.memoria.agregar_grupo_activo(gid, name)
             abrir_chat_ui(gid, nombre_legible=name, es_grupo=True)
             enviar_notificacion("GhostWhisperChat", f"Te has unido a {name}")

        # --- PRIVATE LOGIC ---
        elif tipo == "CHAT_REQ":
            # Peticion de chat privado
            # 1. Check "No Molestar"
            if self.memoria.no_molestar:
                # Auto-deny
                rej = empaquetar("CHAT_NO", {"reason": "Busy"}, self.memoria.get_origen())
                try: sock.sendall(rej)
                except: pass
                return

            # 2. User Prompt (Zenity)
            acepta = preguntar_invitacion_chat(origen['nick'], origen['uid'])
            
            if acepta:
                # Send ACK
                ack = empaquetar("CHAT_ACK", {}, self.memoria.get_origen())
                try: sock.sendall(ack)
                except: pass
                
                # Open UI
                abrir_chat_ui(origen['uid'], nombre_legible=origen['nick'], es_grupo=False)
            else:
                # Send NO
                rej = empaquetar("CHAT_NO", {"reason": "Rejected"}, self.memoria.get_origen())
                try: sock.sendall(rej)
                except: pass

        elif tipo == "CHAT_ACK":
            # Me aceptaron!
            print(f"[WHISPER] ¡{origen['nick']} aceptó el chat!", file=sys.stderr)
            abrir_chat_ui(origen['uid'], nombre_legible=origen['nick'], es_grupo=False)
            enviar_notificacion("GhostWhisperChat", f"{origen['nick']} aceptó tu solicitud.")

        elif tipo == "CHAT_NO":
            # Me rechazaron
            razon = payload.get("reason", "Sin razón")
            print(f"[WHISPER] {origen['nick']} rechazó el chat: {razon}", file=sys.stderr)
            enviar_notificacion("GhostWhisperChat", f"{origen['nick']} rechazó la conexión.")

        elif tipo == "MSG":
             try:
                 target_id = payload.get('gid') or origen['uid']
                 if target_id in self.ui_sessions:
                     self.ui_sessions[target_id].sendall(f"\n[{origen['nick']}]: {payload.get('text')}\n".encode('utf-8'))
                 else:
                     enviar_notificacion(f"Mensaje de {origen['nick']}", payload.get('text'))
             except: pass

    def _hilo_ping(self):
        """Heartbeat UDP"""
        while self.running:
            if not self.memoria.invisible:
                # Broadcast PING implies "I am here"
                # Use DISCOVER packet just to keep cache fresh? Or explicit PING?
                # Using DISCOVER as a 'KeepAlive' signal is efficient
                pkg = empaquetar("DISCOVER", {"filter": "PING"}, self.memoria.get_origen())
                try:
                    self.red.enviar_udp_broadcast(pkg)
                except: pass
            time.sleep(15)

    def tareas_mantenimiento(self):
        # Clean old peers
        self.memoria.limpiar_peers_inactivos()
