# /usr/lib/ghostwhisperchat/datos/contactos.py
# Gestión de Agenda de Contactos

import json
import os
import shutil
import time

CONTACTS_FILE = os.path.expanduser("~/.ghostwhisperchat/contactos.json")

def cargar_contactos():
    if not os.path.exists(CONTACTS_FILE):
        return {}
    
    try:
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def guardar_contactos(contactos_dict):
    tmp_file = CONTACTS_FILE + ".tmp"
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(contactos_dict, f, indent=4)
        shutil.move(tmp_file, CONTACTS_FILE)
    except OSError:
        pass

def agregar_contacto(uid, nick, ip):
    """
    Registra un contacto conocido.
    """
    agenda = cargar_contactos()
    
    # Actualizamos o creamos
    agenda[uid] = {
        "nick": nick,
        "last_ip": ip,
        "last_seen": time.time(),
        "trusted": False, # Por defecto
        "blocked": False
    }
    
    guardar_contactos(agenda)

def bloquear_contacto(uid):
    agenda = cargar_contactos()
    if uid in agenda:
        agenda[uid]["blocked"] = True
        guardar_contactos(agenda)

def es_bloqueado(uid):
    agenda = cargar_contactos()
    if uid in agenda:
        return agenda[uid].get("blocked", False)
    return False

def obtener_nick_conocido(uid):
    agenda = cargar_contactos()
    if uid in agenda:
        return agenda[uid].get("nick")
    return None
