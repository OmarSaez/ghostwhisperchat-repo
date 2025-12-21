# /usr/lib/ghostwhisperchat/core/utilidades.py
# Modulo de utilidades generales para GhostWhisperChat 2.0

import socket
import re
import unicodedata

def get_local_ip():
    """
    Obtiene la IP de la interfaz de red principal que tiene salida al exterior.
    Crea un socket UDP dummy hacia una IP pública (Google DNS) para determinar
    qué interfaz usa el sistema por defecto. No envía datos reales.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # No se necesita establecer conexión real, solo determinar la ruta
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def normalize_text(text):
    """
    Normaliza un texto para comparaciones (IDs, comandos, etc).
    1. Convierte a minúsculas.
    2. Elimina acentos/diacríticos (unidecode-style pero con librería estándar).
    3. Elimina espacios al inicio y final.
    Ej: "Ómar Sáez " -> "omarsaez" (segun arquitectura, aunque el ejemplo decia strip, 
    usualmente ids quitan espacios internos también o normalizan. 
    La arquitectura dice: Quita tildes, mayúsculas y espacios.
    Ejemplo entrada: "Ómar Sáez", Salida: "omarsaez". 
    Así que quitaremos espacios internos también para IDs de grupo, 
    pero cuidado con mensajes. Esta función es para IDs/Normalización estricta.
    """
    if not isinstance(text, str):
        return ""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Eliminar tildes (NFD separation + filtering non-spacing marks)
    text = ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')
    
    # 3. Strip whitespace
    text = text.strip()
    
    # 4. Eliminar espacios internos?
    # User Request Revision: "quitar tildes y espaciados finales como esto 'Sáez ' deberia quedar como 'saez' todo minusculas"
    # User did NOT explicitly ask to remove internal spaces in this request, but previously architecture example did.
    # However, "Sáez " has a trailing space.
    # We will stick to the architecture of removing ALL spaces to be safe for IDs, 
    # unless user specifically wants "Juan Perez" -> "juanperez".
    # Given "Sáez " -> "saez", strip is key.
    
    # Let's ensure strict ID normalization: Remove all spaces.
    text = text.replace(" ", "")
    
    return text

def validar_nick(nick):
    """
    Valida si un nickname cumple con las reglas:
    - Longitud: 3 a 15 caracteres.
    - Caracteres: Alfanuméricos y guion bajo _.
    - Sin espacios.
    """
    if not nick:
        return False
        
    if len(nick) < 3 or len(nick) > 15:
        return False
        
    # Regex: Solo letras, numeros y guion bajo
    patron = r'^[a-zA-Z0-9_]+$'
    if not re.match(patron, nick):
        return False
        
    return True

import subprocess
import os

def enviar_notificacion(titulo, mensaje):
    """Envía una notificación de escritorio simple."""
    try:
        subprocess.Popen(['notify-send', titulo, mensaje])
    except: pass

def preguntar_invitacion_chat(remitente_nick, remitente_id, grupo_nombre=None):
    """
    Muestra un popup Zenity preguntando si acepta la invitación.
    Retorna True (Aceptar) o False (Rechazar/Timeout).
    Timeout de 20 segundos.
    """
    # Si es grupo, mensaje diferente
    if grupo_nombre:
        msg = f"[{remitente_nick}] te está invitando a la sala '{grupo_nombre}'.\n¿Quieres unirte?"
        titulo = "Invitación a Grupo"
    else:
        msg = f"[{remitente_nick}] quiere iniciar un chat privado.\n¿Aceptar?"
        titulo = "Invitación Privada"

    cmd = [
        'zenity', 
        '--question', 
        '--title', titulo, 
        '--text', msg, 
        '--ok-label', 'Sí', 
        '--cancel-label', 'No', 
        '--timeout', '20'
    ]
    
    try:
        # Zenity return codes: 0=OK, 1=Cancel, 5=Timeout
        ret = subprocess.call(cmd)
        return (ret == 0)
    except FileNotFoundError:
        # Fallback si no hay zenity
        return False
