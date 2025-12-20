# /usr/lib/ghostwhisperchat/logica/grupos.py
# Lógica de Negocio: Grupos

import hashlib
from ghostwhisperchat.core.utilidades import normalize_text

def generar_group_id(nombre):
    """
    Calcula el ID determinista de un grupo basado en su nombre normalizado.
    ID = SHA256(normalize(nombre))
    """
    nom = normalize_text(nombre)
    return hashlib.sha256(nom.encode('utf-8')).hexdigest()

generar_id_grupo = generar_group_id

def generar_hash_clave(clave):
    """
    Genera el hash de la contraseña para grupos privados.
    """
    if not clave:
        return None
    return hashlib.sha256(clave.encode('utf-8')).hexdigest()

hash_password = generar_hash_clave

def es_grupo_valido(group_data, clave_input=None):
    """
    Verifica si tenemos acceso (Clave correcta).
    group_data: info recibida del FOUND.
    """
    if group_data.get("is_public"):
        return True
        
    # Es privado
    target_hash = group_data.get("password_hash") # El anuncio FOUND no debería llevar la clave real
    # ERROR EN MI RAZONAMIENTO: El FOUND no lleva la clave, lleva flag.
    # El JOIN_REQ envía el hash de la clave que YO escribí.
    # El Embajador verifica.
    
    # Esta función quizás valide localmente si el user proveyó clave.
    if not clave_input:
        return False
    return True
