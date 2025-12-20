# /usr/lib/ghostwhisperchat/datos/config.py
# Gestor de Configuración (Persistencia en JSON)

import json
import os
import shutil

CONFIG_DIR = os.path.expanduser("~/.ghostwhisperchat")
CONFIG_FILE = os.path.join(CONFIG_DIR, "inter_chat.json")

DEFAULT_CONFIG = {
    "version": "2.0.0",
    "user": {
        "nick": "UsuarioNuevo",
        "uid": "",           # Se generará si está vacío
        "status_msg": "Disponible"
    },
    "preferences": {
        "no_molestar": False,
        "invisible": False,
        "log_chat": True,
        "auto_download": False
    },
    "network": {
        "bind_ip": "0.0.0.0" # Opcional, por si se quiere forzar
    }
}

def inicializar_directorio():
    if not os.path.exists(CONFIG_DIR):
        try:
            os.makedirs(CONFIG_DIR, mode=0o755)
        except OSError as e:
            print(f"Error creando directorio config: {e}")

def cargar_config():
    """
    Carga la configuración desde ~/.ghostwhisperchat/inter_chat.json.
    Si no existe o es inválido, crea uno por defecto.
    """
    inicializar_directorio()
    
    if not os.path.exists(CONFIG_FILE):
        return crear_default()
        
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Merge simple con default por si faltan claves nuevas en upgrades
            # (Una implementación robusta haría deep merge, aqui simple)
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
    except (json.JSONDecodeError, OSError):
        print("Error leyendo config, restaurando default...")
        return crear_default()

def guardar_config(data):
    """
    Guarda el diccionario en disco de forma atómica (write + rename).
    """
    inicializar_directorio()
    
    tmp_file = CONFIG_FILE + ".tmp"
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        
        # Atomic rename
        shutil.move(tmp_file, CONFIG_FILE)
        return True
    except OSError as e:
        print(f"Error guardando config: {e}")
        return False

def crear_default():
    """Genera configuración limpia"""
    import hashlib
    import uuid
    
    # Generar un UID seguro si no existe uno previo
    # Usamos MAC + Random para unicidad
    node_id = uuid.getnode()
    rand_uuid = uuid.uuid4().hex
    raw_id = f"{node_id}-{rand_uuid}"
    uid_hash = hashlib.sha256(raw_id.encode()).hexdigest()[:16] # 16 chars suficiente
    
    config = DEFAULT_CONFIG.copy()
    config["user"]["uid"] = uid_hash
    
    guardar_config(config)
    return config
