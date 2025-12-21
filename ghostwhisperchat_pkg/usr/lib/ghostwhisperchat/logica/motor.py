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
        self.ui_sessions = {} 
        
        # Buffer efímero para resultados de escaneo (--enlinea)
        self.scan_buffer = []
        
        # Trigger temporal para JOIN (buscar y unir)
        self.pending_join_name = None 

    def iniciar_ipc(self):
        if os.path.exists(IPC_SOCK_PATH):
            try:
                os.unlink(IPC_SOCK_PATH)
            except OSError:
                pass
        
        self.ipc_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.ipc_sock.bind(IPC_SOCK_PATH)
        self.ipc_sock.listen(5)
        self.ipc_sock.setblocking(False)

    def bucle_principal(self):
        """Loop principal del Demonio"""
        print("[*] Iniciando Motor GWC v2.1...", file=sys.stderr)
        
        # Determine local IP and Identity
        from ghostwhisperchat.core.utilidades import get_local_ip
        local_ip = get_local_ip()
        self.memoria.mi_ip = local_ip
        print(f"[*] Identidad: {self.memoria.mi_nick} ({self.memoria.mi_uid}) @ {local_ip}", file=sys.stderr)

        if not self.red.iniciar_servidores():
            print("[X] Fallo en red. Abortando.", file=sys.stderr)
            return

        self.iniciar_ipc()
        self.running = True
        
        # Start PING thread
        threading.Thread(target=self._hilo_ping, daemon=True).start()
        
        print(f"[MOTOR_DEBUG] Entrando a Bucle Principal. Running={self.running}", file=sys.stderr)
        
        try:
            while self.running:
                sockets_red = self.red.get_sockets_lectura()
                sockets_ui = list(self.ui_sessions.values())
                rlist = sockets_red + [self.ipc_sock] + sockets_ui
                
                try:
                    readable, _, _ = select.select(rlist, [], [], 2.0)
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
             import traceback
             traceback.print_exc(file=sys.stderr)
        finally:
             self.running = False


    def procesar_ipc_mensaje(self, mensaje, conn):
        """Maneja comandos transitorios y registros de UI"""
        if mensaje.startswith("__REGISTER_UI__"):
            partes = mensaje.split(" ", 2)
            if len(partes) >= 3:
                chat_id = partes[2]
                self.ui_sessions[chat_id] = conn
                print(f"[UI] Registrada ventana para {chat_id}", file=sys.stderr)
                conn.sendall(f"[*] Conectado al Daemon. ID: {chat_id}\n".encode('utf-8'))
            return

        elif mensaje.startswith("REGISTER_UI"):
            parts = mensaje.split(":", 1)
            if len(parts) == 2:
                chat_id = parts[1]
                self.ui_sessions[chat_id] = conn
                print(f"[IPC] UI registrada para chat_id: {chat_id}", file=sys.stderr)
            return

        elif mensaje.startswith("--"):
            respuesta = self.ejecutar_comando_transitorio(mensaje)
            conn.sendall(respuesta.encode('utf-8'))
            conn.close()
        else:
            print(f"[IPC] Mensaje desconocido: {mensaje}", file=sys.stderr)
            conn.close()

    def ejecutar_comando_transitorio(self, comando_str, context_ui=None):
        cmd, args = parsear_comando(comando_str)
        
        if cmd == "HELP":
            return obtener_ayuda_comando(args[0] if args else None)

        elif cmd == "SCAN_RESULTS":
            if not self.scan_buffer:
                return "[*] No se encontraron resultados."
            
            res = "--- RESULTADOS DEL ESCANEO ---\n"
            for item in self.scan_buffer:
                 # Check type of item (User or Group)
                 if item.get("type") == "GROUP":
                      res += f"[SALA] {item['name']} (Ambassador: {item['ip']})\n"
                 else:
                      res += f"[*] {item.get('nick')} ({item.get('ip')})\n"
                      
            self.scan_buffer = [] # Clear after reading
            return res

        elif cmd == "JOIN":
             if not args: return "[X] Uso: --unirse <Nombre>"
             nombre = args[0]
             gid = grupos.generar_id_grupo(nombre)
             
             # Set trigger for auto-join in FOUND handler
             self.pending_join_name = nombre
             
             if gid in self.memoria.grupos_activos:
                 abrir_chat_ui(gid, nombre_legible=nombre, es_grupo=True)
                 return f"[*] Ya estás en '{nombre}'. Abriendo chat."
                 
             pkg = empaquetar("SEARCH", {"group_name": nombre}, self.memoria.get_origen())
             self.red.enviar_udp_broadcast(pkg)
             print(f"[GROUP_DEBUG] Enviando SEARCH UDP para '{nombre}'...", file=sys.stderr)
             return f"[*] Buscando grupo '{nombre}' en la red..."

        elif cmd == "CREATE_PUB":
             if not args: return "[X] Uso: --crearpublico <Nombre>"
             nombre = args[0]
             gid = grupos.generar_id_grupo(nombre)
             self.memoria.agregar_grupo_activo(gid, nombre)
             abrir_chat_ui(gid, nombre_legible=nombre, es_grupo=True)
             return f"[*] Grupo público '{nombre}' creado."

        elif cmd == "CREATE_PRIV":
             if len(args) < 2: return "[X] Uso: --crearprivado <Nombre> <Clave>"
             nombre = args[0]
             clave = args[1]
             gid = grupos.generar_id_grupo(nombre)
             pwd_hash = grupos.hash_password(clave)
             self.memoria.agregar_grupo_activo(gid, nombre, pwd_hash)
             abrir_chat_ui(gid, nombre_legible=nombre, es_grupo=True)
             return f"[*] Grupo privado '{nombre}' creado."

        elif cmd == "SCAN":
             # 1. Limpiar buffer
             self.scan_buffer = []
             # 2. Enviar Broadcast
             pkg = empaquetar("DISCOVER", {"filter": "ALL"}, "ALL")
             self.red.enviar_udp_broadcast(pkg)
             return "[*] Búsqueda lanzada."

        elif cmd == "GLOBAL_STATUS":
             m = self.memoria
             res =  f"--- ESTADO GLOBAL ---\n"
             res += f"UID: {m.mi_uid}\n"
             res += f"Nick: {m.mi_nick}\n"
             res += f"IP: {m.mi_ip}\n"
             res += f"Version: {m.version}\n"
             res += f"Peers: {len(m.peers)}\n"
             return res

        elif cmd == "CONTACTS":
             # Usamos peers para historial reciente por ahora
             ct = self.memoria.peers
             if not ct: return "No hay contactos recientes."
             res = "--- CONTACTOS (Caché) ---\n"
             for ip, data in ct.items():
                  if data['uid'] == self.memoria.mi_uid: continue
                  res += f"[{data['nick']}] ({ip})\n"
             return res

        elif cmd == "SHORTCUTS":
             res = "ABREVIACIONES:\n"
             # Import locally to avoid circular dep if needed, or assume global import
             # from ghostwhisperchat.datos.recursos import ABBREVIATIONS_DISPLAY
             for cat, cmds in ABBREVIATIONS_DISPLAY.items():
                 res += f"\n[{cat}]\n"
                 for sub, data in cmds.items():
                      res += f"  - {sub}: {', '.join(data['aliases'])}\n"
             return res
             
        elif cmd == "DM": 
             if not args: return "[X] Uso: --dm <Usuario>"
             target = args[0]
             peer = self.memoria.buscar_peer(target)
             if not peer:
                 return f"[X] '{target}' no encontrado (Use --enlinea)."
             
             print(f"[WHISPER] Solicitando chat a {peer['nick']}...", file=sys.stderr)
             pkg = empaquetar("CHAT_REQ", {}, self.memoria.get_origen())
             try:
                 self.red.enviar_tcp_priv(peer['ip'], pkg)
                 return f"[*] Solicitud enviada a {peer['nick']}."
             except Exception as e:
                 return f"[X] Fallo: {e}"

        elif cmd == "CHANGE_NICK":
            if not args: return "[X] Uso: --nick <Nuevo>"
            old = self.memoria.mi_nick
            self.memoria.mi_nick = args[0]
            self.memoria.guardar_configuracion()
            return f"[*] Nick cambiado: {old} -> {self.memoria.mi_nick}"

        elif cmd == "MUTE_TOGGLE":
            self.memoria.no_molestar = not self.memoria.no_molestar
            self.memoria.guardar_configuracion()
            return f"[*] No Molestar: {self.memoria.no_molestar}"

        elif cmd == "VISIBILITY_TOGGLE":
            self.memoria.invisible = not self.memoria.invisible
            self.memoria.guardar_configuracion()
            return f"[*] Invisible: {self.memoria.invisible}"
            
        elif cmd == "LOG_TOGGLE":
             self.memoria.log_chat = not self.memoria.log_chat
             return f"[*] Log: {self.memoria.log_chat}"
             
        elif cmd == "DL_TOGGLE":
             self.memoria.auto_download = not self.memoria.auto_download
             return f"[*] Auto-Descarga: {self.memoria.auto_download}"
             
        elif cmd == "LS":
             if not context_ui: return "[X] Solo en chat."
             chat_id = context_ui[1]
             if chat_id in self.memoria.grupos_activos:
                 g = self.memoria.grupos_activos[chat_id]
                 ms = g.get('miembros', {})
                 # ms is dict {uid: {nick, ip, status...}}
                 res = f"Miembros en '{g['nombre']}': {len(ms)}\n"
                 for uid, mdata in ms.items():
                     nick = mdata.get('nick')
                     ip = mdata.get('ip')
                     status = mdata.get('status', 'UNK')
                     tag = " [Tu]" if uid == self.memoria.mi_uid else ""
                     res += f" - {nick} ({ip}) [{status}]{tag}\n"
                 return res
             return "Chat Privado."

        elif cmd == "LIST_GROUPS":
            # 1. Limpiar buffer de escaneo (reusamos scan_buffer o filtramos)
            self.scan_buffer = [] 
            # 2. Enviar Broadcast Discovery de Grupos
            pkg = empaquetar("DISCOVER", {"filter": "GROUPS"}, "ALL")
            self.red.enviar_udp_broadcast(pkg)
            return "[*] Buscando grupos públicos..."

        elif cmd == "EXIT":
            if context_ui:
                 # User typed --salir IN CHAT
                 # We trigger client close, which triggers disconnect_ui, which triggers LEAVE/BYE
                 return "[*] Cerrando chat... __CLOSE_UI__"
            
            # Global Shutdown
            self._shutdown_all_sessions()
            self.running = False
            return "[*] Apagando..."
            
        elif cmd == "CLEAR":
            return "\033c"

        return f"[?] Comando: {comando_str}"


    def procesar_input_chat_ui(self, ui_sock, mensaje):
        msg_content = ""
        chat_id = None
        
        if mensaje.startswith("__MSG__"):
            msg_content = mensaje.replace("__MSG__ ", "", 1)
            for uid, s in self.ui_sessions.items():
                if s == ui_sock:
                    chat_id = uid
                    break
        elif ":" in mensaje:
            parts = mensaje.split(":", 1)
            chat_id = parts[0]
            msg_content = parts[1]
        
        if chat_id and msg_content:
             if msg_content.startswith("--"):
                 contexto = ("UI", chat_id)
                 res = self.ejecutar_comando_transitorio(msg_content, context_ui=contexto)
                 ui_sock.sendall(f"\n[SISTEMA] {res}\n".encode('utf-8'))
                 return

             ui_sock.sendall(f"Tu: {msg_content}\n".encode('utf-8'))
             
             if chat_id in self.memoria.grupos_activos:
                 g = self.memoria.grupos_activos[chat_id]
                 pkg = empaquetar("MSG", {"text": msg_content, "gid": chat_id}, self.memoria.get_origen())
                 
                 from ghostwhisperchat.core.transporte import PORT_GROUP
                 members = g.get('miembros', {})
                 # Normalize to list
                 m_list = members.values() if isinstance(members, dict) else members
                 
                 # Send to all peers
                 for m in m_list:
                     uid = m.get('uid')
                     if uid == self.memoria.mi_uid: continue
                     ip = m.get('ip')
                     if not ip: continue
                     
                     try:
                         # Transient connection for message
                         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                         s.settimeout(1.0) # Fast timeout
                         s.connect((ip, PORT_GROUP))
                         s.sendall(pkg + b'\n')
                         s.close()
                     except: pass 
             else:
                 peer = self.memoria.buscar_peer(chat_id)
                 if peer:
                     pkg = empaquetar("MSG", {"text": msg_content}, self.memoria.get_origen())
                     try: self.red.enviar_tcp_priv(peer['ip'], pkg)
                     except: pass

    def _shutdown_all_sessions(self):
        print("[SHUTDOWN] Cerrando todas las sesiones...", file=sys.stderr)
        # Iterate copy of keys because desconectar_ui modifies dict
        for chat_id, sock in list(self.ui_sessions.items()):
            # Simulate disconnect which triggers LEAVE/BYE
            # We can't rely on socket close triggering select loop because we are stopping loop
            # So we call logic manually
            self.desconectar_ui(sock)

    def desconectar_ui(self, ui_sock):
        for chat_id, sock in list(self.ui_sessions.items()):
            if sock == ui_sock:
                del self.ui_sessions[chat_id]
                try: ui_sock.close()
                except: pass
                
                # Logic for notifying exit
                # 1. Is it a Group?
                if chat_id in self.memoria.grupos_activos:
                     g = self.memoria.grupos_activos[chat_id]
                     # Send LEAVE to all members
                     leave_pkg = empaquetar("LEAVE", {"gid": chat_id}, self.memoria.get_origen())
                     from ghostwhisperchat.core.transporte import PORT_GROUP
                     members = g.get('miembros', {})
                     m_list = members.values() if isinstance(members, dict) else members
                     
                     for m in m_list:
                         uid = m.get('uid')
                         if uid == self.memoria.mi_uid: continue
                         ip = m.get('ip')
                         if not ip: continue
                         try:
                             s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                             s.settimeout(0.5)
                             s.connect((ip, PORT_GROUP))
                             s.sendall(leave_pkg + b'\n')
                             s.close()
                         except: pass
                         
                # 2. Is it a Private Peer? (chat_id is UID)
                else:
                    peer = self.memoria.buscar_peer(chat_id)
                    if peer:
                        bye_pkg = empaquetar("CHAT_BYE", {}, self.memoria.get_origen())
                        try: self.red.enviar_tcp_priv(peer['ip'], bye_pkg)
                        except: pass
                
                return

    # --- MANEJO RED (UDP + TCP) ---

    def manejar_paquete_udp(self, data_bytes, addr):
        valid, data = desempaquetar(data_bytes)
        if not valid: return

        tipo = data.get("tipo")
        payload = data.get("payload")
        origen = data.get("origen")

        if origen:
            # User Request: Do NOT save UDP scan results to persistent contacts.
            # Only TCP interactions (Chat) should save to contacts.
            # self.memoria.actualizar_peer(addr[0], origen['uid'], origen['nick'])
            pass

        if tipo == "SEARCH":
            target_name = payload.get("group_name")
            print(f"[GROUP_DEBUG] Recibido SEARCH para '{target_name}'", file=sys.stderr)
            for gid, gdata in self.memoria.grupos_activos.items():
                if gdata['nombre'] == target_name:
                    print(f"[GROUP_DEBUG] Grupo encontrado localmente. Respondiendo FOUND.", file=sys.stderr)
                    resp = empaquetar("FOUND", {"type": "GROUP", "name": target_name, "gid": gid}, self.memoria.get_origen())
                    try: self.red.sock_udp.sendto(resp, addr)
                    except: pass

        elif tipo == "DISCOVER":
            filt = payload.get("filter", "ALL")
            
            # Responder Presente si soy visible (PEER scan)
            if (filt == "ALL" or filt == "PEERS") and not self.memoria.invisible:
                 resp = empaquetar("FOUND", {"type": "PEER", "status": "ONLINE"}, self.memoria.get_origen())
                 try: self.red.sock_udp.sendto(resp, addr)
                 except: pass
            
            # Responder con mis grupos PUBLICOS si piden GROUPS
            if filt == "ALL" or filt == "GROUPS":
                 for gid, g in self.memoria.grupos_activos.items():
                     if g['es_publico']:
                         # Respondemos con FOUND tipo GROUP
                         resp = empaquetar("FOUND", {"type": "GROUP", "name": g['nombre'], "gid": gid}, self.memoria.get_origen())
                         try: self.red.sock_udp.sendto(resp, addr)
                         except: pass
        
        elif tipo == "FOUND":
            ftype = payload.get("type")
            
            if ftype == "PEER":
                peer_data = {
                    "nick": origen['nick'],
                    "ip": addr[0],
                    "status": payload.get("status")
                }
                # Evitar duplicados en el buffer
                if not any(x['ip'] == addr[0] for x in self.scan_buffer):
                    self.scan_buffer.append(peer_data)

            if ftype == "GROUP":
                gid = payload.get("gid")
                name = payload.get("name")
                ambassador_ip = addr[0]
                print(f"[RADAR] Grupo encontrado: {name} en {ambassador_ip}", file=sys.stderr)
                
                # Add to scan buffer if not present (Discovery)
                group_entry = {"type": "GROUP", "name": name, "gid": gid, "ip": ambassador_ip}
                if not any(x.get('gid') == gid for x in self.scan_buffer):
                      self.scan_buffer.append(group_entry)

                # Auto-Join Logic (Only if triggered by JOIN command)
                if self.pending_join_name == name:
                    print(f"[MESH] Auto-Joining found group: {name}...", file=sys.stderr)
                    self.pending_join_name = None # Clear trigger
                    
                    if gid not in self.memoria.grupos_activos:
                        req_pkg = empaquetar("JOIN_REQ", {"gid": gid, "password_hash": None}, self.memoria.get_origen())
                        try:
                            from ghostwhisperchat.core.transporte import PORT_GROUP
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.connect((ambassador_ip, PORT_GROUP))
                            s.sendall(req_pkg + b'\n')
                            self.red.registrar_socket_tcp(s, f"GRP_OUT_{gid}")
                        except Exception as e:
                            print(f"[X] Fallo al conectar con Grupo: {e}", file=sys.stderr)

    def manejar_paquete_tcp(self, data_bytes, sock):
        valid, data = desempaquetar(data_bytes)
        if not valid: return
        
        tipo = data.get("tipo")
        payload = data.get("payload")
        origen = data.get("origen")
        
        if origen:
             self.memoria.actualizar_peer(origen['ip'], origen['uid'], origen['nick'])

        if tipo == "JOIN_REQ":
            gid = payload.get("gid")
            if gid in self.memoria.grupos_activos:
                g = self.memoria.grupos_activos[gid]
                
                # 1. Add to our own list (Ambassador)
                if 'miembros' not in g: g['miembros'] = {}
                # We need the full details of the joiner. Paradoxically, the 'origen' header has it.
                if origen:
                    g['miembros'][origen['uid']] = {'nick': origen['nick'], 'ip': origen['ip'], 'uid': origen['uid']}
                    print(f"[GROUP] Agregado nuevo miembro: {origen['nick']} ({origen['ip']})", file=sys.stderr)
                
                # 2. Send WELCOME
                welcome = empaquetar("WELCOME", {"gid": gid, "name": g['nombre']}, self.memoria.get_origen())
                try: sock.sendall(welcome + b'\n')
                except: pass
                
                # 3. Send SYNC (List of current members, including the new one so they know they are in)
                members = g.get('miembros', [])
                sync_list = []
                # If 'miembros' is a dict in memory, convert to list.
                if isinstance(members, dict):
                     sync_list = list(members.values())
                elif isinstance(members, list):
                     sync_list = members
                     
                sync_pkg = empaquetar("SYNC", {"gid": gid, "members": sync_list}, self.memoria.get_origen())
                try: sock.sendall(sync_pkg + b'\n')
                except: pass

        elif tipo == "WELCOME":
             gid = payload.get("gid")
             name = payload.get("name")
             self.memoria.agregar_grupo_activo(gid, name)
             abrir_chat_ui(gid, nombre_legible=name, es_grupo=True)
             enviar_notificacion("GhostWhisperChat", f"Te has unido a {name}")

        elif tipo == "SYNC":
             gid = payload.get("gid")
             members = payload.get("members", [])
             if gid in self.memoria.grupos_activos:
                 g = self.memoria.grupos_activos[gid]
                 if 'miembros' not in g: g['miembros'] = {}
                 
                 # Importante: Conectar y Anunciarse
                 for m in members:
                     uid = m.get('uid')
                     if uid == self.memoria.mi_uid: continue
                     
                     g['miembros'][uid] = m
                     # TODO: Logic to connect to these peers if not connected, and send ANNOUNCE
                     # Por simplicidad v2, asumimos que ANNOUNCE es broadcast o multicast.
                     # Pero en TCP Mesh, debemos conectar punto a punto.
                     
                 # Si acabamos de unirnos (SYNC recibido), anunciamos nuestra llegada
                 # A todos los miembros conocidos
                 ann_pkg = empaquetar("ANNOUNCE", {"gid": gid, "user": self.memoria.get_origen()}, self.memoria.get_origen())
                 
                 from ghostwhisperchat.core.transporte import PORT_GROUP
                 for m in members:
                     uid = m.get('uid')
                     if uid == self.memoria.mi_uid: continue
                     
                     target_ip = m.get('ip')
                     if not target_ip: continue

                     # Intento de conexion mesh
                     try:
                         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                         s.settimeout(2.0) # Timeout corto
                         s.connect((target_ip, PORT_GROUP))
                         s.sendall(ann_pkg + b'\n')
                         self.red.registrar_socket_tcp(s, f"GRP_MESHSEND_{gid}_{uid}")
                     except Exception as e:
                         print(f"[MESH] Fallo anuncio a {target_ip}: {e}", file=sys.stderr)
                 
        elif tipo == "ANNOUNCE":
             gid = payload.get("gid")
             new_user = payload.get("user")
             if gid in self.memoria.grupos_activos:
                 g = self.memoria.grupos_activos[gid]
                 if 'miembros' not in g: g['miembros'] = {}
                 if new_user:
                     g['miembros'][new_user['uid']] = new_user
                     
                     # Notificar en el chat
                     if gid in self.ui_sessions:
                         self.ui_sessions[gid].sendall(f"\n[SISTEMA] {new_user['nick']} se unió al grupo.\n".encode('utf-8'))

        elif tipo == "LEAVE":
             gid = payload.get("gid")
             uid = origen['uid'] if origen else None
             
             if gid in self.memoria.grupos_activos and uid:
                 g = self.memoria.grupos_activos[gid]
                 if 'miembros' in g and uid in g['miembros']:
                     del g['miembros'][uid]
                     if gid in self.ui_sessions:
                         self.ui_sessions[gid].sendall(f"\n[SISTEMA] {origen['nick']} abandonó el grupo.\n".encode('utf-8'))

        elif tipo == "CHAT_REQ":
            if self.memoria.no_molestar:
                rej = empaquetar("CHAT_NO", {"reason": "Busy"}, self.memoria.get_origen())
                try: sock.sendall(rej + b'\n')
                except: pass
                return

            acepta = preguntar_invitacion_chat(origen['nick'], origen['uid'])
            if acepta:
                ack = empaquetar("CHAT_ACK", {}, self.memoria.get_origen())
                try: sock.sendall(ack + b'\n')
                except: pass
                abrir_chat_ui(origen['uid'], nombre_legible=origen['nick'], es_grupo=False)
            else:
                rej = empaquetar("CHAT_NO", {"reason": "Rejected"}, self.memoria.get_origen())
                try: sock.sendall(rej + b'\n')
                except: pass

        elif tipo == "CHAT_ACK":
            abrir_chat_ui(origen['uid'], nombre_legible=origen['nick'], es_grupo=False)
            enviar_notificacion("GhostWhisperChat", f"{origen['nick']} aceptó tu solicitud.")

        elif tipo == "CHAT_NO":
            razon = payload.get("reason", "Sin razón")
            enviar_notificacion("GhostWhisperChat", f"{origen['nick']} rechazó la conexión.")
            
        elif tipo == "CHAT_BYE":
             # Notify termination
             uid = origen['uid']
             if uid in self.ui_sessions:
                 s = self.ui_sessions[uid]
                 s.sendall(f"\n[SISTEMA] {origen['nick']} cerró la sesión.\n".encode('utf-8'))
                 # Instruct client to close after delay
                 s.sendall(b"__CLOSE_UI__")
                 # We keep our UI open so user can see history or exit manually.

        elif tipo == "MSG":
             text = payload.get("text")
             gid = payload.get("gid")
             target_id = gid if gid else origen['uid']
             
             if target_id in self.ui_sessions:
                 self.ui_sessions[target_id].sendall(f"\n[{origen['nick']}]: {text}\n".encode('utf-8'))
             else:
                 enviar_notificacion(f"Mensaje de {origen['nick']}", text)

    def _hilo_ping(self):
        while self.running:
            if not self.memoria.invisible:
                pkg = empaquetar("DISCOVER", {"filter": "PING"}, self.memoria.get_origen())
                try: self.red.enviar_udp_broadcast(pkg)
                except: pass
            time.sleep(15)

    def tareas_mantenimiento(self):
        self.memoria.limpiar_peers_inactivos()
