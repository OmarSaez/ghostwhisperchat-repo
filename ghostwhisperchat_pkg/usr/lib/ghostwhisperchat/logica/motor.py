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
        
        print(f"[MOTOR_DEBUG] Entrando a Bucle Principal. Running={self.running}", file=sys.stderr)
        
        try:
            while self.running:
                # Lista de sockets a vigilar: Red + IPC + UI Clients Activos
                sockets_red = self.red.get_sockets_lectura()
                sockets_ui = list(self.ui_sessions.values())
                
                # print(f"[MOTOR_DEBUG] Loop tick. Sockets Red={len(sockets_red)} IPC={1} UI={len(sockets_ui)}", file=sys.stderr)
                
                rlist = sockets_red + [self.ipc_sock] + sockets_ui
                
                try:
                    # Timeout 5s para ver prints de vida
                    readable, _, _ = select.select(rlist, [], [], 5.0)
                except select.error as e:
                    print(f"[MOTOR_DEBUG] Select Error: {e}", file=sys.stderr)
                    # Si el error es EINTR (interrupcion de señal) seguimos
                    if e.args[0] == 4: # EINTR
                        continue
                    else:
                        raise e # Re-raise si es grave
                except Exception as e:
                    print(f"[MOTOR_DEBUG] Excepcion Generica en Select: {e}", file=sys.stderr)
                    raise e
                    
                if not readable:
                    # Timeout
                    # print("[MOTOR_DEBUG] Select Timeout (Idle)", file=sys.stderr)
                    continue

                for s in readable:
                    # 1. IPC Listener (Nuevas conexiones locales)
                    if s == self.ipc_sock:
                        print("[MOTOR_DEBUG] Actividad en IPC Socket (Nueva conexión entrante)", file=sys.stderr)
                        try:
                            # Accept para sacar al cliente de la cola de espera
                            conn, _ = s.accept()
                            conn.setblocking(True) 
                            
                            # Leer mensaje (hasta 4k)
                            data = conn.recv(4096)
                            if data:
                                texto = data.decode('utf-8').strip()
                                print(f"[MOTOR_DEBUG] IPC Rx: {texto}", file=sys.stderr)
                                self.procesar_ipc_mensaje(texto, conn)
                            else:
                                print("[MOTOR_DEBUG] IPC Conexión vacía (Probe)", file=sys.stderr)
                                conn.close()
                        except Exception as e:
                            print(f"[MOTOR_DEBUG] Error en handling IPC: {e}", file=sys.stderr)
                    
                    # 2. Mensajes de UIs ya conectadas (User Input en chat windows)
                    elif s in sockets_ui:
                        try:
                            data = s.recv(4096)
                            if data:
                                self.procesar_input_chat_ui(s, data.decode('utf-8'))
                            else:
                                print("[MOTOR_DEBUG] UI socket cerrado (EOF)", file=sys.stderr)
                                self.desconectar_ui(s)
                        except:
                            self.desconectar_ui(s)
    
                    # 3. UDP Discovery
                    elif s == self.red.sock_udp:
                        try:
                            data, addr = s.recvfrom(65535)
                            print(f"[MOTOR_DEBUG] UDP Rx de {addr}", file=sys.stderr)
                            self.manejar_paquete_red(data, addr, "UDP")
                        except Exception as e:
                            print(f"[MOTOR_DEBUG] Error lectura UDP: {e}", file=sys.stderr)

                    # 4. TCP Listeners
                    elif s == self.red.sock_tcp_group or s == self.red.sock_tcp_priv:
                         self.red.aceptar_conexion(s) # Acepta y añade a lista interna de inputs

                    # 5. TCP Datos (Red Messages)
                    else: 
                        # Puede ser un socket de red...
                        try:
                            data = s.recv(8192)
                            if data:
                                parts = data.split(b'\n')
                                for p in parts:
                                    if p:
                                        self.manejar_paquete_red(p, s.getpeername(), "TCP", s)
                        except OSError:
                             self.red.cerrar_tcp(s)

                self.tareas_mantenimiento()

        except Exception as e:
             print(f"[MOTOR_DEBUG] !!! CRASH EN BUCLE PRINCIPAL !!!: {e}", file=sys.stderr)
             import traceback
             traceback.print_exc(file=sys.stderr)
             raise e
        finally:
             print(f"[MOTOR_DEBUG] Bucle finalizado. Running={self.running}", file=sys.stderr)


    # --- MANEJO IPC / COMANDOS LOCALES ---
    
    def procesar_ipc_mensaje(self, texto, conn):
        """
        Maneja tanto comandos transitorios ("--dm ...") 
        como registros de UI ("__REGISTER_UI__ ...")
        """
        if texto.startswith("__REGISTER_UI__"):
            # Es una ventana de chat persistente
            # Formato: __REGISTER_UI__ TIPO ID
            partes = texto.split(" ", 2)
            if len(partes) >= 3:
                chat_id = partes[2]
                self.ui_sessions[chat_id] = conn
                print(f"[UI] Registrada ventana para {chat_id}")
                # Le mandamos historial reciente si tuvieramos...
                conn.sendall(f"[*] Conectado al Daemon. ID: {chat_id}\n".encode('utf-8'))
            return # NO cerramos la conexión

        elif texto.startswith("__MSG__"):
            # Esto deberia venir por el socket persistente, pero por si acaso
            pass

        else:
            # Comando Transitorio Normal
            result_msg = self.ejecutar_comando_transitorio(texto)
            conn.sendall(result_msg.encode('utf-8'))
            conn.close() # Transitorio = Cierra al terminar

    def procesar_input_chat_ui(self, sock_ui, texto):
        # Mensajes que escribe el usuario en la ventana
        if texto.startswith("__MSG__"):
            msg_content = texto.replace("__MSG__ ", "", 1)
            # Buscar quien es este socket
            chat_id = None
            for uid, s in self.ui_sessions.items():
                if s == sock_ui:
                    chat_id = uid
                    break
            
            if chat_id:
                # 1. ¿Es un comando?
                if msg_content.startswith("--") or msg_content.startswith("/"):
                     # Ejecutar como comando transitorio
                     # Por ahora, solo ejecutamos y logueamos.
                     # v2.25: Mandamos el contexto para validaciones (ej: ADD)
                     contexto_actual = ("UI", chat_id) # Podríamos enriquecer con tipo privado/grupo
                     
                     res = self.ejecutar_comando_transitorio(msg_content, context_ui=contexto_actual)
                     
                     # Enviar respuesta de vuelta a la UI con prefijo SISTEMA
                     if res:
                         sock_ui.sendall(f"\n[SISTEMA] {res}\n".encode('utf-8'))
                     return

                # 2. Es un mensaje normal
                print(f"[DEBUG] Enviando msg a {chat_id}: {msg_content}")
                
                # ECO LOCAL: "Tu: mensaje"
                sock_ui.sendall(f"Tu: {msg_content}\n".encode('utf-8'))
                
                # IMPLEMENTACION REAL V2.1 TCP PRIVADO:
                try:
                    # TODO: Implementar lookup real
                    # peer = self.memoria.obtener_peer(chat_id) 
                    pass
                except Exception as e:
                    print(f"[!] Error enviando mensaje a {chat_id}: {e}", file=sys.stderr)

    def desconectar_ui(self, sock):
        to_del = None
        for uid, s in self.ui_sessions.items():
            if s == sock:
                to_del = uid
                break
        if to_del:
            del self.ui_sessions[to_del]
            try:
                sock.close()
            except:
                pass
            print(f"[UI] Ventana {to_del} cerrada.")

    def ejecutar_comando_transitorio(self, cmd_raw, context_ui=None):
        # Parseamos con logica de comandos anterior
        print(f"[MOTOR_DEBUG] Procesando comando raw: {cmd_raw} Context={context_ui}", file=sys.stderr)
        cmd, args = parsear_comando(cmd_raw)
        print(f"[MOTOR_DEBUG] Parseado: CMD='{cmd}' Type={type(cmd)} ARGS={args}", file=sys.stderr)
        
        if cmd == "GLOBAL_STATUS":
             # --info ENRIQUECIDO
             m = self.memoria
             res =  f"--- ESTADO GLOBAL ---\n"
             res += f"UID: {m.mi_uid}\n"
             res += f"Nick: {m.mi_nick}\n"
             res += f"IP: {m.mi_ip}\n"
             res += f"Versión: {m.version}\n"
             res += f"Peers conocidos: {len(m.peers)}\n"
             res += f"Chats activos (UI): {len(self.ui_sessions)}\n"
             
             p_udp = self.red.sock_udp.getsockname()[1] if self.red.sock_udp else "?"
             p_grp = self.red.sock_tcp_group.getsockname()[1] if self.red.sock_tcp_group else "?"
             p_priv = self.red.sock_tcp_priv.getsockname()[1] if self.red.sock_tcp_priv else "?"
             
             res += f"Puertos: UDP:{p_udp} TCP_GRP:{p_grp} TCP_PRIV:{p_priv}\n"
             
             # Variables de Configuración
             res += f"No Molestar: {'ON' if m.no_molestar else 'OFF'}\n"
             res += f"Invisible: {'ON' if m.invisible else 'OFF'}\n"
             res += f"Auto-Descarga: {'ON' if m.auto_download else 'OFF'}\n"
             res += f"Log Chat: {'ON' if m.log_chat else 'OFF'}"
             return res

        elif cmd == "DM": 
             if not args: return "[X] Uso: --dm <Usuario>"
             dest = args[0]
             abrir_chat_ui(dest, nombre_legible=dest, es_grupo=False)
             return f"[*] Abriendo chat con {dest}..."

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

        elif cmd == "JOIN":
             if not args: return "[X] Uso: --unirse <Nombre>"
             nombre = args[0]
             gid = grupos.generar_id_grupo(nombre)
             abrir_chat_ui(gid, nombre_legible=nombre, es_grupo=True)
             return f"[*] Uniendo a grupo '{nombre}'..."

        elif cmd == "SCAN":
             pkg = empaquetar("DISCOVER", {"filter": "ALL"}, "ALL")
             self.red.enviar_udp_broadcast(pkg)
             
             m = self.memoria
             if not m.peers:
                 return "[*] Señal enviada. Nadie detectado AÚN.\n    (Espera unos segundos)"
             
             res = "[*] Usuarios detectados en caché:\n"
             count = 0
             for ip, data in m.peers.items():
                 if data['uid'] == m.mi_uid: continue
                 res += f" - {data['nick']} ({ip})\n"
                 count += 1
             if count == 0: return "[*] Señal enviada. (0 encontrados)"
             return res

        elif cmd == "LS":
             if not context_ui: return "[X] Solo en chat."
             chat_id = context_ui[1]
             if chat_id in self.memoria.grupos_activos:
                 g = self.memoria.grupos_activos[chat_id]
                 miembros = g.get('miembros', [])
                 if not miembros: return f"[*] Grupo '{g['nombre']}': Sin miembros listados."
                 return f"[*] Miembros: {', '.join(miembros)}"
             else:
                 return f"[*] Chat Privado: Tú y el remoto."

        elif cmd == "ADD":
             if not context_ui: return "[X] Solo en chat."
             chat_id = context_ui[1]
             if chat_id not in self.memoria.grupos_activos:
                 return "[X] Solo puedes invitar en grupos."
             return f"[*] Invitando (Stub)..."

        elif cmd == "CONTACTS":
             # Usamos peers para historial reciente por ahora
             ct = self.memoria.peers
             if not ct: return "No hay contactos recientes."
             res = "--- CONTACTOS (Caché) ---\n"
             for ip, data in ct.items():
                  if data['uid'] == self.memoria.mi_uid: continue
                  res += f"[{data['nick']}] ({ip})\n"
             return res

        elif cmd == "EXIT":
             if context_ui:
                 chat_id = context_ui[1]
                 s = self.ui_sessions.get(chat_id)
                 if s: self.desconectar_ui(s)
                 return "[*] Cerrando chat..."
             else:
                 self.running = False
                 return "[!] Apagando Demonio..."

        elif cmd == "HELP":
             return AYUDA

        elif cmd == "SHORTCUTS":
             res = "ABREVIACIONES:\n"
             for cat, cmds in ABBREVIATIONS_DISPLAY.items():
                 res += f"\n[{cat}]\n"
                 for sub, data in cmds.items():
                      res += f"  - {sub}: {', '.join(data['aliases'])}\n"
             return res

        elif cmd == "CLEAR":
             return "\033c[*] Pantalla limpia."

        elif cmd == "LOG_TOGGLE":
             self.memoria.log_chat = not self.memoria.log_chat
             return f"[*] Historial: {'ON' if self.memoria.log_chat else 'OFF'}"

        elif cmd == "DL_TOGGLE":
             self.memoria.auto_download = not self.memoria.auto_download
             return f"[*] Auto-Descarga: {'ON' if self.memoria.auto_download else 'OFF'}"

        elif cmd == "MUTE_TOGGLE":
            self.memoria.no_molestar = not self.memoria.no_molestar
            return f"[*] No Molestar: {'ON' if self.memoria.no_molestar else 'OFF'}"
            
        elif cmd == "VISIBILITY_TOGGLE":
            self.memoria.invisible = not self.memoria.invisible
            return f"[*] Invisible: {'ON' if self.memoria.invisible else 'OFF'}"

        elif cmd == "CHANGE_NICK":
            if not args: return "[X] Uso: --nick <Nuevo>"
            old = self.memoria.mi_nick
            self.memoria.mi_nick = args[0]
            return f"[*] Nick cambiado: {old} -> {self.memoria.mi_nick}"

        elif cmd == "STATUS":
             return f"[*] Estado actualizado: {' '.join(args)}"
             
        elif cmd == "LIST_GROUPS":
            return "Escaneando grupos... (Pendiente)"

        return f"[?] Comando recibido: {cmd_raw}"

    # --- MANEJO RED INCOMING ---

    def manejar_paquete_red(self, data_bytes, addr, proto, sock_tcp=None):
        valid, data = desempaquetar(data_bytes)
        if not valid: return
        
        tipo = data.get("tipo")
        payload = data.get("payload")
        origen = data.get("origen")
        
        # Identity housekeeping
        if origen:
             # Hack para memoria: necesitamos guardar UID -> IP
             self.memoria.actualizar_peer(origen['ip'], origen['uid'], origen['nick'])

        if tipo == "CHAT_REQ":
            # Alguien quiere hablar.
            # 1. Preguntar al usuario (Zenity)
            acepta = preguntar_invitacion_chat(origen['nick'], origen['uid'])
            
            if acepta:
                # 2. Mandar ACK (Pendiente implementar envio)
                # ... enviar_tcp(CHAT_ACK) ...
                
                # 3. Abrir Ventana
                abrir_chat_ui(origen['uid']) # Usamos UID como ID unico
            else:
                pass # Mandar REJECT

        elif tipo == "MSG":
            # Mensaje entrante.
            # ¿Tengo ventana abierta para esto?
            # origen['uid'] es el ID del chat privado
            chat_id = origen['uid']
            
            if chat_id in self.ui_sessions:
                # Si, enviar al socket UI
                s_ui = self.ui_sessions[chat_id]
                fmt_msg = f"\n[{origen['nick']}]: {payload.get('text')}\n"
                try:
                    s_ui.sendall(fmt_msg.encode('utf-8'))
                except:
                    pass
            else:
                # No hay ventana? Notificar y quizás abrir?
                enviar_notificacion(f"Mensaje de {origen['nick']}", payload.get('text'))
                # Opcional: Auto abrir si no es spam
                
    def tareas_mantenimiento(self):
        pass
