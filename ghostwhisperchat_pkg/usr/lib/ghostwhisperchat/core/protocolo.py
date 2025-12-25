# /usr/lib/ghostwhisperchat/core/protocolo.py
# Protocolo de Comunicación JSON

import json
import time
from ghostwhisperchat.core.estado import MemoriaGlobal

CMD_TYPES = [
    "SEARCH", "FOUND", "DISCOVER", "PING",     # UDP
    "JOIN_REQ", "WELCOME", "SYNC", "ANNOUNCE", "MSG", "LEAVE", # TCP GROUP
    "CHAT_REQ", "CHAT_ACK", "CHAT_NO", "FILE_OFFER", "FILE_ACCEPT", "FILE_REJECT" # TCP PRIVATE
]

def empaquetar(tipo, payload, destino, token=""):
    """
    Crea el paquete JSON estándar.
    :param tipo: String (Enum CMD_TYPES)
    :param payload: Dict con los datos específicos
    :param destino: GID (Hash) o UID/IP destino
    """
    memoria = MemoriaGlobal()
    
    paquete = {
        "ver": 2,
        "tipo": tipo,
        "token": token,
        "origen": memoria.get_origen(),
        "destino": destino,
        "payload": payload,
        "meta": {
            "ts": int(time.time()),
            # Si estamos en un grupo, podríamos añadir el nombre, 
            # pero por ahora lo dejamos genérico o vacío si no aplica.
            "grp_name": "" 
        }
    }
    
    # Serializar a bytes UTF-8
    try:
        data_json = json.dumps(paquete)
        return data_json.encode('utf-8')
    except TypeError as e:
        print(f"Error serializando JSON: {e}")
        return None

def desempaquetar(data_bytes):
    """
    Parsea bytes a Dict y valida estructura básica.
    Retorna (valid, content_dict_or_error_str)
    """
    if not data_bytes:
        return False, "Empty data"

    try:
        decoded = data_bytes.decode('utf-8')
        data = json.loads(decoded)
    except UnicodeDecodeError:
        return False, "UTF-8 Decode Error"
    except json.JSONDecodeError:
        return False, "JSON Syntax Error"
    
    if not isinstance(data, dict):
        return False, "Not a dictionary"
        
    # Validar campos base
    valid, err = validar_schema(data)
    if not valid:
        return False, err
        
    # Validar version (Backward compatibility check could go here)
    if data.get("ver") != 2:
        return False, f"Unsupported version: {data.get('ver')}"

    return True, data

def validar_schema(data):
    """
    Verifica que existan las llaves maestras.
    """
    keys_needed = ["ver", "tipo", "origen", "destino", "payload"]
    for k in keys_needed:
        if k not in data:
            return False, f"Missing field: {k}"
            
    # Validar origen
    origen = data["origen"]
    if not isinstance(origen, dict):
         return False, "Field 'origen' must be dict"
         
    if "uid" not in origen or "nick" not in origen or "ip" not in origen:
        return False, "Incomplete 'origen' struct"
        
    return True, None
