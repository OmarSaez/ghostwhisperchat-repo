# /usr/lib/ghostwhisperchat/logica/comandos.py
# Intérprete de Comandos (Parser)

import shlex
from ghostwhisperchat.datos.recursos import COMMAND_MAP, ABBREVIATIONS_DISPLAY, AYUDA

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

def obtener_ayuda_comando(cmd_raw=None):
    if not cmd_raw:
        return AYUDA
        
    # Buscar ayuda especifica
    buscar = cmd_raw.lower().lstrip('-')
    
    for cat, cmds in ABBREVIATIONS_DISPLAY.items():
        for sub, data in cmds.items():
            # Check aliases stripping dashes
            clean_aliases = [a.lstrip('-') for a in data['aliases']]
            if buscar in clean_aliases:
                return f"\n{Colores.BOLD}[{sub}]{Colores.RESET}\n  {data['desc']}\n  Alias: {', '.join(data['aliases'])}\n"
    
    return f"No se encontró ayuda para '{cmd_raw}'. Escribe --ayuda para ver todo."

from ghostwhisperchat.datos.recursos import Colores
