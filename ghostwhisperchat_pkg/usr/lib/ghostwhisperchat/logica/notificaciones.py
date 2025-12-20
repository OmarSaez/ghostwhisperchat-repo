# /usr/lib/ghostwhisperchat/logica/notificaciones.py
# Sistema de Notificaciones v2.1 (Zenity First)

import subprocess
import time
import shutil
from ghostwhisperchat.core.estado import MemoriaGlobal

_SPAM_CACHE = {} 
SPAM_COOLDOWN = 60 

def enviar_notificacion(titulo, mensaje, urgencia="normal"):
    """
    Envía notificación efímera (notify-send).
    """
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-u", urgencia, titulo, mensaje])

def preguntar_invitacion_chat(origen_nick, origen_id, es_grupo=False):
    """
    Muestra un diálogo Modal (Bloqueante para el thread que lo llama, ojo).
    Zenity return: 0=Yes, 1=No/Cancel.
    """
    tipo = "Grupo" if es_grupo else "Privado"
    texto = f"{origen_nick} te invita a un chat {tipo}.\n¿Aceptar?"
    
    if not shutil.which("zenity"):
        # Fallback sin UI: Rechazar por seguridad
        return False
        
    try:
        # Usamos timeout para no bloquear eternamente el daemon si el user no está
        # zenity --question --timeout=30 (segundos)
        res = subprocess.call([
            "zenity", "--question", 
            "--title", f"Invitación de {origen_nick}", 
            "--text", texto,
            "--ok-label", "Aceptar",
            "--cancel-label", "Ignorar",
            "--timeout", "60" 
        ])
        return (res == 0)
    except OSError:
        return False

def mostrar_error(msg):
    if shutil.which("zenity"):
        subprocess.Popen(["zenity", "--error", "--text", msg])

def should_notify(evento_tipo, origen_uid=None):
    memoria = MemoriaGlobal()
    if memoria.no_molestar:
        if origen_uid:
            last = _SPAM_CACHE.get(origen_uid, 0)
            if (time.time() - last) < SPAM_COOLDOWN:
                return True
        return False
    return True

def registrar_evento_notificacion(origen_uid):
    if origen_uid:
        _SPAM_CACHE[origen_uid] = time.time()
