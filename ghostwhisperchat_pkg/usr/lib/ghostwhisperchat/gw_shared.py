
import os
import sys
import platform
import subprocess
import socket
import threading
import time
import hashlib

# v38.0: Shared Definitions for Modular Architecture
APP_VER_NUM = 42.37
APP_VER_TAG = "Fix: NameError exec_lobby_cmd restored"
APP_VERSION = f"v{APP_VER_NUM} ({APP_VER_TAG})"

# --- CONFIG POP ANTI-SPAM ---
POP_RESET_TIME = 60   # Seconds of inactivity required to reset pop counter
MAX_POPS_BURST = 2    # Max pops shown per active conversation burst

# --- AFK LOGIC ---
AFK_TIMEOUT = 30      # Seconds to auto-mark as AFK if invite ignored


# --- UTILS ---
def calculate_file_hash(path):
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def normalize_str(s):
    if not s: return ""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', s.strip()) if unicodedata.category(c) != 'Mn').lower()


# --- CONSTANTS ---
IPC_PORT = 5000 
SEP = "<SEPARATOR>"

class Colors:
    H, B, G, W, F, E, BO = '\033[95m', '\033[94m', '\033[92m', '\033[93m', '\033[91m', '\033[0m', '\033[1m'
    C, M, WH = '\033[96m', '\033[95m', '\033[97m'
    R = F # Alias for Red
    PALETTE = [B, C, M, W, WH]

    @staticmethod
    def get_col(n):
        return Colors.PALETTE[sum(ord(c) for c in n) % len(Colors.PALETTE)] if n else Colors.WH

# --- COMMAND DEFINITIONS ---
COMMAND_DEFS = {
    'CHAT_GROUP': {
        'aliases': ['--chatgrupal', '--grupal', '--grupo', '--chatg', '--g', '-g', '--cg', '-cg', '--group', '--grp', '-grp'],
        'desc': 'Crear/Unirse a sala de Grupal (ID + Pass).'
    },
    'CHAT_PRIV': {
        'aliases': ['--chatpersonal', '--personal', '--chatp', '--p', '-p', '--cp', '-cp', '--dm', '-dm', '--private', '--priv', '-priv', '--msg', '-m'],
        'desc': 'Iniciar chat privado con IP o Nick.'
    },
    'LS': {
        'aliases': ['--ls', '-l', '--l', '--list', '--lista', '--members'],
        'desc': 'Listar chats activos (Lobby) o miembros (Chat).'
    },
    'SCAN': {
        'aliases': ['--quienes', '-q', '--q', '--who', '-w', '--scan'],
        'desc': 'Escanear red en busca de usuarios.'
    },
    'CONTACTS': {
        'aliases': ['--contactos', '--c', '-c', '--history', '--historial', '--k', '-k', '--contacts'],
        'desc': 'Ver historial de usuarios conocidos.'
    },
    'NICK': {
        'aliases': ['--nick', '--nombre', '--nickname', '--name', '-n', '--n'],
        'desc': 'Cambiar tu nombre de usuario visible.'
    },
    'STATUS': {
        'aliases': ['--estado', '--status', '--st', '-e', '--e', '-s', '--s'],
        'desc': 'Cambiar tu estado (ej: Ocupado).'
    },
    'INVITE': {
        'aliases': ['--invite', '--invitar', '--inv', '-i', '--i'],
        'desc': 'Invitar usuarios a la sala actual.'
    },
    'FILE': {
        'aliases': ['--archivo', '--arch', '--file', '-f', '--f', '-a', '--a', '--send', '--enviar'],
        'desc': 'Enviar archivo a la sala actual.'
    },
    'SCAN_VIS_ON': {
        'aliases': ['--quienes-si', '--visible', '-v', '--v', '--vis-on'],
        'desc': 'Hacerse visible en escaneos.'
    },
    'SCAN_VIS_OFF': {
        'aliases': ['--quienes-no', '--invisible', '--hidden', '-h', '--h', '--vis-off'],
        'desc': 'Ocultarse en escaneos.'
    },
    'LOG_ON': {
        'aliases': ['--log-on', '--logon', '--save-on', '-Lon'],
        'desc': 'Activar guardado de historial.'
    },
    'LOG_OFF': {
        'aliases': ['--log-off', '--logoff', '--save-off', '-Loff'],
        'desc': 'Desactivar guardado de historial.'
    },

    'AUTOSTART_ON': {
        'aliases': ['--autolevantado-si', '--boot-on', '--startup-on'],
        'desc': 'Iniciar app al arrancar sistema (Linux).'
    },
    'AUTOSTART_OFF': {
        'aliases': ['--autolevantado-no', '--boot-off', '--startup-off'],
        'desc': 'No iniciar app al arrancar.'
    },
    'DL_ON': {
        'aliases': ['--descarga-si', '--dl-si', '--dl-on', '--auto-dl-on', '--descarga-automatica-si'],
        'desc': 'Aceptar descargas automáticamente (Sin preguntar).'
    },
    'DL_OFF': {
        'aliases': ['--descarga-no', '--dl-no', '--dl-off', '--auto-dl-off', '--descarga-automatica-no'],
        'desc': 'Preguntar antes de descargar cada archivo.'
    },
    'ACCEPT': {
        'aliases': ['--aceptar', '--accept', '--ok', '-y', '--y', '--yes', '--acc'],
        'desc': 'Aceptar invitación pendiente.'
    },
    'DENY': {
        'aliases': ['--rechazar', '--deny', '--no', '-no', '-d', '--d', '--cancel'],
        'desc': 'Rechazar invitación pendiente.'
    },
    'EXIT': {
        'aliases': ['--salir', '--exit', '--quit', '-x', '--x', '--close'],
        'desc': 'Salir del chat o cerrar app.'
    },
    'CLEAR': {
        'aliases': ['--limpiar', '--limpieza', '--clear', '--cls', '-cls', '--clean'],
        'desc': 'Limpiar pantalla.'
    },
    'SHORTCUTS': {
        'aliases': ['--abreviaciones', '--shortcuts', '--alias', '-ab', '--ab', '--help-alias'],
        'desc': 'Ver lista de comandos y sus variantes.'
    },
    'HELP': {
        'aliases': ['--help', '--ayuda', '-?', '--?', '--comandos'],
        'desc': 'Ver ayuda general.'
    },
    'GLOBAL_STATUS': {
        'aliases': ['--estados-globales', '--global-status', '--gst', '-gst', '--status-full'],
        'desc': 'Ver resumen de toda la configuración actual.'
    },
    'DEBUG': {
        'aliases': ['--debug', '--dbg', '-dbg'],
        'desc': 'Activar/Desactivar logs de depuración.'
    },
    'UPDATE': {
        'aliases': ['--update', '--actualizar', '--up'],
        'desc': 'Buscar e instalar actualizaciones del repositorio.'
    },
    'VERSION': {
        'aliases': ['--version', '--ver', '-v'],
        'desc': 'Mostrar la versión actual instalada.'
    },
    'INTEGRITY': {
        'aliases': ['--integridad', '--integrity', '--check', '--test', '-t'],
        'desc': 'Realizar autodiagnóstico de integridad del sistema.'
    }
}

# Mapa plano para búsqueda rápida O(1)
CMD_MAP = {}
for k, v in COMMAND_DEFS.items():
    for alias in v['aliases']:
        CMD_MAP[alias] = k

def resolve_cmd(inp_cmd):
    """Devuelve la KEY canónica del comando o None"""
    return CMD_MAP.get(inp_cmd)

def get_desktop_path():
    if platform.system() == "Linux":
        try:
            return subprocess.check_output(["xdg-user-dir", "DESKTOP"]).decode().strip()
        except: pass
    elif platform.system() == "Windows":
        try:
            return os.path.join(os.environ['USERPROFILE'], 'Desktop')
        except: pass
    
    # Fallback
    home = os.path.expanduser("~")
    for d in ["Desktop", "Escritorio"]:
        p = os.path.join(home, d)
        if os.path.exists(p): return p
    return home

def get_ip():
    # Optimization: Use a dummy socket to get preferred outgoing IP without actual connection
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            # Google DNS IP (doesn't need to be reachable)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except:
        return "127.0.0.1"

class Loader:
    """Animación de carga simple para CLI (Context Manager)"""
    def __init__(self, desc="Cargando"):
        self.desc = desc
        self.stop_event = threading.Event()
        self.t = threading.Thread(target=self._animate, daemon=True)
        self.is_tty = sys.stdout.isatty()

    def __enter__(self):
        if self.is_tty: self.t.start()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.stop_event.set()
        if self.is_tty: 
             self.t.join()
             # Clean line
             sys.stdout.write("\r" + " " * (len(self.desc) + 10) + "\r")
             sys.stdout.flush()

    def _animate(self):
        chars = [".  ", " . ", "  ."]
        i = 0
        while not self.stop_event.is_set():
            sys.stdout.write(f"\r{self.desc} [{chars[i]}]")
            sys.stdout.flush()
            time.sleep(0.3)
            i = (i + 1) % len(chars)

