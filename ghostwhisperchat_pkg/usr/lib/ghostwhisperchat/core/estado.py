# /usr/lib/ghostwhisperchat/core/estado.py
# Gestión de Estado Global (Singleton)

import threading
import time
from ghostwhisperchat.datos.recursos import APP_VERSION

class MemoriaGlobal:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MemoriaGlobal, cls).__new__(cls)
                cls._instance._inicializar()
            return cls._instance

    def _inicializar(self):
        # Datos Propios
        self.mi_uid = None       # Hash único persistente
        self.mi_nick = "Usuario" # Nick actual
        self.mi_ip = None        # IP local
        
        # Configuración Runtime
        self.no_molestar = False
        self.invisible = False
        self.log_chat = False
        self.auto_download = False
        self.version = APP_VERSION

        # Tablas de Red
        self.peers = {} 
        # Estructura PEERS: 
        # { 
        #   "IP": { 
        #       "uid": "...", 
        #       "nick": "...", 
        #       "status": "ONLINE", 
        #       "last_seen": timestamp 
        #   } 
        # }

        # Grupos
        self.grupos_activos = {}
        # Estructura GRUPOS:
        # {
        #   "gid": {
        #       "nombre": "...",
        #       "es_publico": True,
        #       "miembros": [ ...list of IPs... ],
        #       "mensajes": [ ...list of msg dicts... ],
        #       "clave_hash": "..." (opt)
        #   }
        # }
        
        # Buzón Privado (Mensajes pendients de leer o historial sesion actual)
        self.buzon_privado = [] 
        # Lista de dicts {origen_nick, texto, ts, ...}
        
        # Estado de Chat Actual (UI Context)
        self.chat_actual_tipo = None # 'GRUPO' o 'PRIVADO' o None
        self.chat_actual_id = None   # GID o IP del peer

    def set_identidad(self, uid, nick, ip):
        self.mi_uid = uid
        self.mi_nick = nick
        self.mi_ip = ip

    def actualizar_peer(self, ip, uid, nick, status="ONLINE"):
        with self._lock:
            self.peers[ip] = {
                "uid": uid,
                "nick": nick,
                "status": status,
                "last_seen": time.time()
            }

    def obtener_peer(self, ip):
        return self.peers.get(ip)

    def limpiar_peers_antiguos(self, timeout_segundos=60):
        """Elimina peers que no han dado señales de vida"""
        ahora = time.time()
        with self._lock:
            # Crear lista a eliminar para no modificar dict mientras iteramos
            borrar = [ip for ip, data in self.peers.items() 
                      if (ahora - data['last_seen']) > timeout_segundos]
            for ip in borrar:
                del self.peers[ip]

    def agregar_grupo_activo(self, gid, nombre, clave_hash=None):
        """Registra un grupo en la memoria local"""
        with self._lock:
            if gid not in self.grupos_activos:
                self.grupos_activos[gid] = {
                    "nombre": nombre,
                    "es_publico": (clave_hash is None),
                    "miembros": [],
                    "mensajes": [],
                    "clave_hash": clave_hash
                }

    def buscar_peer(self, query):
        """Busca un peer por Nick (comienzo) o UID exacto"""
        query = query.lower()
        with self._lock:
            for ip, p in self.peers.items():
                if p['nick'].lower() == query or p['uid'] == query:
                    # Devolvemos una copia enriquecida con IP
                    ret = p.copy()
                    ret['ip'] = ip
                    return ret
        return None
