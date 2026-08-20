import threading
import time
import os
import sys
import json
import hashlib
import getpass
from ghostwhisperchat.datos.recursos import APP_VERSION

CONFIG_FILE = os.path.expanduser("~/.ghostwhisperchat/config.json")
HISTORY_DIR = os.path.expanduser("~/.ghostwhisperchat/history")

class MemoriaGlobal:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MemoriaGlobal, cls).__new__(cls)
                cls._instance._inicializar()
            return cls._instance

    def _inicializar(self):
        # Datos Propios
        self.mi_uid = None       # Hash único persistente
        self.mi_nick = os.getenv("USER", "Usuario") # Nick actual (Default: System User)
        self.sys_user = getpass.getuser() # Real System Username (Immutable)
        self.mi_ip = None        # IP local
        self.mi_onion = None     # Dirección Tor Onion v3 (GWC-ID Global)
        self.mi_estado_msg = None # Mensaje de estado personalizado (max 34 chars)
        
        # Configuración Runtime
        self.no_molestar = False
        self.invisible = False
        self.privacy_policy = "AMBOS" # "AMBOS", "IP", "TOR", "NADA"
        self.log_chat = False
        self.auto_download = False
        self.version = APP_VERSION
        
        # Cargar Persistencia
        self._cargar_configuracion()
        self._cargar_contactos()
        
        # --- DETERMINISTIC UID (v2.137) ---
        # El usuario pidio asociar historial a "Cuenta Linux + Hardware" para evitar perdidas al cambiar Nick.
        # Intentamos generar un UID robusto basado en MachineID + SysUser + MAC Address.
        # Si falla, usamos el aleatorio legado o el del config.
        
        try:
            # 1. Get Machine ID
            machine_id = None
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    machine_id = f.read().strip()
            elif os.path.exists("/var/lib/dbus/machine-id"):
                with open("/var/lib/dbus/machine-id", "r") as f:
                    machine_id = f.read().strip()
            
            # 2. Get Sys User
            sys_user = self.sys_user # already loaded
            
            # 3. Get MAC Address (Physical Layer Uniqueness)
            import uuid
            mac_addr = uuid.getnode()
            
            if machine_id and sys_user:
                # Deterministic Seed: User + OS_ID + Hardware_MAC
                # Robust even against disk cloning (if MAC differs)
                seed = f"{sys_user}@{machine_id}@{mac_addr}"
                stable_uid = hashlib.sha256(seed.encode()).hexdigest()[:16]
                self.mi_uid = stable_uid
            else:
                # Fallback to random if no machine-id
                if not self.mi_uid:
                     random_seed = f"{time.time()}-{os.getpid()}"
                     self.mi_uid = hashlib.sha256(random_seed.encode()).hexdigest()[:16]
        except Exception as e:
            print(f"[!] Error generando UID estable: {e}", file=sys.stderr)
            if not self.mi_uid:
                 self.mi_uid = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

        self.guardar_configuracion() # Persist current Choice

        # Tablas de Red
        self.peers = {} 
        # Estructura PEERS: 
        # { 
        #   "UID": { 
        #       "uid": "...", 
        #       "nick": "...", 
        #       "ip": "...",
        #       "onion": "...",
        #       "status": "ONLINE", 
        #       "last_seen": timestamp 
        #   } 
        # }

        # Grupos
        self.grupos_activos = {}
        
        # Ignorados temporales (para que al eliminar un contacto no vuelva a aparecer al instante por un ping)
        self.contactos_ignorados = set()
        
        # Buzón Privado (Mensajes pendients de leer o historial sesion actual)
        self.buzon_privado = [] 
        
        # Estado de Chat Actual (UI Context)
        self.chat_actual_tipo = None # 'GRUPO' o 'PRIVADO' o None
        self.chat_actual_id = None   # GID o IP/UID del peer

    def _cargar_configuracion(self):
        print(f"[ESTADO] Cargando config desde {CONFIG_FILE}...", file=sys.stderr)
        if os.path.exists(CONFIG_FILE):
             try:
                 with open(CONFIG_FILE, 'r') as f:
                     data = json.load(f)
                     self.mi_uid = data.get("uid")
                     self.mi_nick = data.get("nick", "Usuario")
                     self.mi_onion = data.get("onion")
                     # Opcional: Cargar settings
                     self.no_molestar = data.get("no_molestar", False)
                     self.invisible = data.get("invisible", False)
                     self.privacy_policy = data.get("privacy_policy", "AMBOS")
                     self.mi_estado_msg = data.get("estado_msg")
                 print(f"[ESTADO] Config cargada. Nick: {self.mi_nick}", file=sys.stderr)
             except Exception as e:
                 print(f"[!] Error cargando config: {e}", file=sys.stderr)
        else:
             print(f"[ESTADO] No existe archivo config.", file=sys.stderr)

    def guardar_configuracion(self):
        """Persiste identidad y preferencias a disco"""
        data = {
            "uid": self.mi_uid,
            "nick": self.mi_nick,
            "onion": self.mi_onion,
            "no_molestar": self.no_molestar,
            "invisible": self.invisible,
            "privacy_policy": self.privacy_policy,
            "estado_msg": self.mi_estado_msg
        }
        try:
             os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
             with open(CONFIG_FILE, 'w') as f:
                 json.dump(data, f)
        except Exception as e:
             print(f"[!] Error guardando config: {e}")

    # --- PERSISTENCIA CONTACTOS ---
    def _cargar_contactos(self):
        cfile = os.path.expanduser("~/.ghostwhisperchat/contacts.json")
        if os.path.exists(cfile):
            try:
                with open(cfile, 'r') as f:
                    self.contactos = json.load(f)
            except: self.contactos = {}
        else:
            self.contactos = {}

    def guardar_contactos(self):
        cfile = os.path.expanduser("~/.ghostwhisperchat/contacts.json")
        try:
            with open(cfile, 'w') as f:
                json.dump(self.contactos, f)
        except: pass

    def registrar_contacto(self, uid, nick, ip, onion=None, sys_user=None, status_msg=None, remote_privacy="AMBOS"):
        """Registra un contacto persistente (historial de interaccion) sin guardar IP/Onion en JSON"""
        if self.privacy_policy == "NADA":
            return # No guardar nada si la politica es NADA (efimero)
            
        if hasattr(self, 'contactos_ignorados') and uid in self.contactos_ignorados:
            return # Ignorar auto-registro si fue eliminado en esta sesion

        from ghostwhisperchat.core.cripto_vault import update_vault_entry
        with self._lock:
            contacto_previo = self.contactos.get(uid, {})
            sys_user_final = sys_user if sys_user else contacto_previo.get("sys_user", "?")
            status_msg_final = status_msg if status_msg is not None else contacto_previo.get("status_msg", "")
            
            # Update public metadata in contacts.json
            self.contactos[uid] = {
                "uid": uid,
                "nick": nick,
                "sys_user": sys_user_final,
                "status_msg": status_msg_final,
                "last_seen": time.time()
            }
            
            # Store private data in vault respetando la privacidad del otro
            save_ip = ip if remote_privacy in ["AMBOS", "IP", "SOLO-LOCAL"] else None
            save_onion = onion if remote_privacy in ["AMBOS", "TOR", "SOLO-GLOBAL"] else None
            
            if save_ip or save_onion:
                update_vault_entry(uid, ip=save_ip, onion=save_onion)
            else:
                from ghostwhisperchat.core.cripto_vault import delete_vault_entry
                delete_vault_entry(uid)

        self.guardar_contactos()
        
    def buscar_contacto_fuzzy(self, query):
        """
        Busca en contactos y peers activos.
        Retorna lista de sugerencias [ {nick, ip, match_ratio, source} ]
        """
        import difflib
        from ghostwhisperchat.core.utilidades import normalize_text
        
        query_norm = normalize_text(query)
        candidates = {}
        
        # 1. Merge sources (Active Peers + Persistent Contacts)
        # Peers have priority on IP info
        all_users = {} 
        
        with self._lock:
            # Load contacts first
            for uid, c in self.contactos.items():
                all_users[uid] = c.copy()
                all_users[uid]['source'] = 'CONTACTO'
                
            # Overwrite/Add active peers (more recent status)
            for ip, p in self.peers.items():
                uid = p.get('uid')
                if uid:
                    p_data = p.copy()
                    p_data['ip'] = ip
                    p_data['source'] = 'RED (Scan)'
                    all_users[uid] = p_data

        suggestions = []
        
        for uid, data in all_users.items():
            nick = data.get('nick', 'UNK')
            nick_norm = normalize_text(nick)
            
            # Exact Match (already checked elsewhere usually, but good to have)
            if query_norm == nick_norm:
                data['ratio'] = 1.0
                suggestions.append(data)
                continue
                
            # Contains
            if query_norm in nick_norm:
                data['ratio'] = 0.9
                suggestions.append(data)
                continue
            
            # Fuzzy
            ratio = difflib.SequenceMatcher(None, query_norm, nick_norm).ratio()
            if ratio >= 0.55: # User requested 55%
                data['ratio'] = ratio
                suggestions.append(data)
        
        # Sort by ratio
        suggestions.sort(key=lambda x: x['ratio'], reverse=True)
        return suggestions

    def set_identidad(self, uid, nick, ip, port_priv=None, port_group=None, onion=None):
        # Este metodo se suele llamar al inicio desde motor para setear IP, Onion y Puertos
        if uid: self.mi_uid = uid
        if nick: self.mi_nick = nick
        self.mi_ip = ip
        if onion: self.mi_onion = onion
        if port_priv: self.mi_port_priv = port_priv
        if port_group: self.mi_port_group = port_group

    def actualizar_peer(self, ip, uid, nick, status="ONLINE", port_priv=None, port_group=None, sys_user=None, status_msg=None, onion=None, remote_privacy="AMBOS"):
        with self._lock:
            if uid not in self.peers:
                self.peers[uid] = {}
            
            update_data = {
                "uid": uid,
                "nick": nick,
                "ip": ip,
                "status": status,
                "last_seen": time.time()
            }
            if sys_user: update_data['sys_user'] = sys_user
            if status_msg is not None: update_data['status_msg'] = status_msg
            if onion: update_data['onion'] = onion
            
            self.peers[uid].update(update_data)
            if port_priv: self.peers[uid]['port_priv'] = port_priv
            if port_group: self.peers[uid]['port_group'] = port_group
            
            # Persistencia Automatica
            self.registrar_contacto(uid, nick, ip, onion=onion, sys_user=sys_user, status_msg=status_msg, remote_privacy=remote_privacy)

    def obtener_peer(self, uid):
        return self.peers.get(uid)

    def limpiar_peers_antiguos(self, timeout_segundos=86400):
        """Elimina peers que no han dado señales de vida"""
        ahora = time.time()
        with self._lock:
            # Iterate UIDs
            borrar = [uid for uid, data in self.peers.items() 
                      if (ahora - data.get('last_seen', 0)) > timeout_segundos]
            for uid in borrar:
                del self.peers[uid]

    def agregar_grupo_activo(self, gid, nombre, clave_hash=None):
        """Registra un grupo en la memoria local"""
        with self._lock:
            if gid not in self.grupos_activos:
                self.grupos_activos[gid] = {
                    "nombre": nombre,
                    "es_publico": (clave_hash is None),
                    "miembros": {
                        self.mi_uid: {
                            "uid": self.mi_uid,
                            "nick": self.mi_nick,
                            "ip": self.mi_ip,
                            "onion": self.mi_onion,
                            "sys_user": self.sys_user,
                            "status": "ONLINE",
                            "port_priv": getattr(self, 'mi_port_priv', 44494),
                            "port_group": getattr(self, 'mi_port_group', 44496)
                        }
                    },
                    "mensajes": [],
                    "clave_hash": clave_hash
                }

    def buscar_peer(self, query):
        """Busca un peer por Nick (comienzo), UID exacto o dirección .onion."""
        query = query.lower()
        candidates = []
        with self._lock:
            for uid, p in self.peers.items():
                if p.get('nick', '').lower() == query or uid == query or p.get('onion', '').lower() == query:
                    candidates.append(p)
        
        if not candidates:
            return None
        
        # Sort by last_seen descending
        candidates.sort(key=lambda x: x.get('last_seen', 0), reverse=True)
        return candidates[0]
        
    def get_origen(self):
        """Devuelve el dict estándar 'origen' para paquetes. Siempre incluimos IP/Onion para el ruteo de red, pero añadimos nuestra politica de privacidad para que el receptor sepa qué guardar permanentemente."""
        origen = {
            "nick": self.mi_nick,
            "uid": self.mi_uid,
            "sys_user": self.sys_user,
            "status_msg": self.mi_estado_msg,
            "port_priv": getattr(self, 'mi_port_priv', 44494),
            "port_group": getattr(self, 'mi_port_group', 44496),
            "ip": self.mi_ip,
            "privacy_policy": getattr(self, 'privacy_policy', "AMBOS")
        }
        
        if self.mi_onion:
            origen["onion"] = self.mi_onion
            
        return origen

    # Alias para compatibilidad
    limpiar_peers_inactivos = limpiar_peers_antiguos

    # --- HISTORIAL ROBUSTO (Feature 2 - Persistence) ---
    def log_historial(self, chat_id, nick_sender, mensaje, es_propio=False):
        """
        Guarda un mensaje en el log del chat específico.
        Formato: [HH:MM] Nick: Mensaje
        """
        try:
            os.makedirs(HISTORY_DIR, exist_ok=True)
            log_path = os.path.join(HISTORY_DIR, f"{chat_id}.log")
            
            from datetime import datetime
            now = datetime.now()
            ts_str = now.strftime("%Y-%m-%d %H:%M")
            time_str = now.strftime("%H:%M")
            
            nick_display = "Tú" if es_propio else nick_sender
            
            # Simple line format for parsing later if needed, or just display
            # We prefix with TS| for internal parsing or just raw text?
            # User wants visual history. Let's store raw display text + hidden meta if needed.
            # But to insert "HOY", we need the date. So let's store:
            # YYYY-MM-DD HH:MM|Nick|Msg
            
            line = f"{ts_str}|{nick_display}|{mensaje}\n"
            
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(line)
            
            # FIX v2.168: Rotacion de Logs (Mantener Max 20 lineas)
            # El usuario solicito que el historial no crezca infinitamente.
            try:
                msg_limit = 20
                with open(log_path, 'r', encoding='utf-8') as fr:
                    lines = fr.readlines()
                
                if len(lines) > msg_limit:
                    keep = lines[-msg_limit:]
                    with open(log_path, 'w', encoding='utf-8') as fw:
                        fw.writelines(keep)
            except: pass
                
        except Exception as e:
            print(f"[X] Error guardando historial: {e}", file=sys.stderr)

    def get_historial_reciente(self, chat_id, limit=15):
        """
        Recupera las últimas líneas formateadas con separadores de fecha.
        Retorna una cadena lista para imprimir.
        """
        log_path = os.path.join(HISTORY_DIR, f"{chat_id}.log")
        if not os.path.exists(log_path):
            return ""
            
        lines = []
        try:
            # Read all (lightweight enough for text logs usually) or tail
            with open(log_path, 'r', encoding='utf-8') as f:
                raw_lines = f.readlines()
                
            # Take last N
            chunk = raw_lines[-limit:] if len(raw_lines) > limit else raw_lines
            
            from datetime import datetime
            from ghostwhisperchat.datos.recursos import Colores
            
            res = ""
            last_date = None
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Header
            if raw_lines:
                res += f"{Colores.GREY}--- Cargar historial previo ({len(chunk)}/{len(raw_lines)}) ---{Colores.RESET}\n"

            for line in chunk:
                parts = line.strip().split('|', 2)
                if len(parts) < 3: continue
                
                dt_str, nick, msg = parts
                date_part, time_part = dt_str.split(' ')
                
                # Date Separator
                if date_part != last_date:
                    if date_part == today:
                        label = "HOY"
                    else:
                        label = date_part
                        
                    res += f"\n{Colores.BG_YELLOW}{Colores.BLACK_TXT} {label} {Colores.RESET}\n"
                    last_date = date_part
                
                # Format: [HH:MM] Nick: Msg
                # Colorize Nick
                if nick == "Tú":
                    c_nick = Colores.C_GREEN_NEON
                else:
                    c_nick = Colores.C_BLUE_ROYAL
                    
                res += f"{Colores.GREY}[{time_part}]{Colores.RESET} {c_nick}{nick}{Colores.RESET}: {msg}\n"
            
            res += f"{Colores.GREY}--- Fin del historial ---{Colores.RESET}\n"
            return res
            
        except Exception as e:
            return f"[Error leyendo historial: {e}]"
