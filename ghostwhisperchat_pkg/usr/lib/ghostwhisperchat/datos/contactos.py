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

def agregar_contacto(uid, nick, ip, onion=None):
    """
    Registra un contacto conocido con su IP local y/o dirección Onion.
    """
    agenda = cargar_contactos()
    
    contacto_previo = agenda.get(uid, {})
    onion_final = onion if onion else contacto_previo.get("onion")
    
    agenda[uid] = {
        "nick": nick,
        "last_ip": ip,
        "onion": onion_final,
        "last_seen": time.time(),
        "trusted": contacto_previo.get("trusted", False),
        "blocked": contacto_previo.get("blocked", False)
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

def buscar_contacto_por_onion(onion_addr):
    """Busca en la agenda si existe un contacto con la dirección .onion dada"""
    agenda = cargar_contactos()
    for uid, data in agenda.items():
        if data.get("onion") == onion_addr:
            return uid, data
    return None, None

def eliminar_contacto(nick_o_uid):
    """
    Elimina un contacto de la agenda buscando por nick (case-insensitive) o por uid exacto.
    Retorna el nick eliminado si tuvo éxito, o None si no se encontró.
    """
    agenda = cargar_contactos()
    uid_a_borrar = None
    nick_encontrado = None

    # Buscar primero por uid exacto
    if nick_o_uid in agenda:
        uid_a_borrar = nick_o_uid
        nick_encontrado = agenda[nick_o_uid].get("nick", nick_o_uid)
    else:
        # Buscar por nick (case-insensitive)
        for uid, data in agenda.items():
            if isinstance(data, dict) and data.get("nick", "").lower() == nick_o_uid.lower():
                uid_a_borrar = uid
                nick_encontrado = data.get("nick", nick_o_uid)
                break

    if uid_a_borrar:
        del agenda[uid_a_borrar]
        guardar_contactos(agenda)
        return nick_encontrado

    return None

def eliminar_todos_contactos():
    """
    Elimina toda la agenda de contactos.
    Retorna el número de contactos eliminados.
    """
    agenda = cargar_contactos()
    total = len(agenda)
    guardar_contactos({})
    return total
