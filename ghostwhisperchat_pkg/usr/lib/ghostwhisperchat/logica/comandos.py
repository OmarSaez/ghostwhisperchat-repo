# /usr/lib/ghostwhisperchat/logica/comandos.py
# Intérprete de Comandos (Parser)

import shlex
from ghostwhisperchat.datos.recursos import COMMAND_MAP, ABBREVIATIONS_DISPLAY

def parsear_comando(texto_input):
    """
    Analiza la línea de comandos del usuario.
    Retorna: (COMANDO_KEY, [argumentos]) o (None, None)
    """
    texto = texto_input.strip()
    if not texto:
        return None, None
        
    try:
        partes = shlex.split(texto)
    except ValueError:
        # Error de comillas sin cerrar
        return "ERROR_SYNTAX", "Comillas desbalanceadas"
        
    if not partes:
        return None, None
        
    cmd_raw = partes[0].lower()
    args = partes[1:]
    
    # Buscar en el mapa
    found_cmd = None
    for key, aliases in COMMAND_MAP.items():
        if cmd_raw in aliases:
            found_cmd = key
            break
            
    # Si no es un comando con --, chequeamos si es un mensaje de chat (si no empieza con -)
    if not found_cmd:
        if not cmd_raw.startswith("-"):
            return "MSG", [texto] # Texto completo original
        else:
            return "UNKNOWN", [cmd_raw]
            
    return found_cmd, args

def obtener_ayuda_comando(cmd_key):
    # Iterar el diccionario de display para encontrar la desc
    # Esto es ineficiente pero el dict es pequeño
    for category in ABBREVIATIONS_DISPLAY.values():
        for item in category.values():
            # item es {'aliases': [], 'desc': ''}
            # No tenemos la key lógica aquí fácil, pero podemos inferir
            pass 
    return "Ayuda detallada pendiente."
