# /usr/lib/ghostwhisperchat/core/launcher.py
# Lanzador de Terminales Agnostico (v2.1)

import shutil
import subprocess
import os

# Lista de terminales soportadas en orden de preferencia
TERMINALES = [
    # (Binario, Argumento para ejecutar comando)
    ('gnome-terminal', '--'), 
    ('mate-terminal', '--'),
    ('xfce4-terminal', '-x'),
    ('konsole', '-e'),
    ('terminator', '-x'),
    ('tilix', '-e'),
    ('xterm', '-e'),
]

def detectar_terminal():
    """Retorna el binario y el flag de ejecución de la terminal disponible"""
    for term, flag in TERMINALES:
        if shutil.which(term):
            return term, flag
    return None, None

def abrir_chat_ui(id_destino, es_grupo=False):
    """
    Abre una nueva ventana de terminal ejecutando el modo UI del cliente.
    Ejecuta: gwc --chat-ui <ID>
    """
    term, flag = detectar_terminal()
    
    if not term:
        # Fallback critico si no hay terminal grafica detectada
        print(f"[X] No se detectó terminal compatible para abrir chat con {id_destino}")
        return False
        
    # Construimos el comando
    # gwc debe estar en el PATH o usamos path absoluto
    cmd_gwc = "gwc" # Asumimos que está instalado en /usr/bin/gwc o en PATH
    
    # Argumentos para el cliente
    # --chat-ui ID --group si es grupo
    args_gwc = [cmd_gwc, "--chat-ui", id_destino]
    if es_grupo:
        args_gwc.append("--group")
        
    # Comando final para subprocess
    # Ejemplo: ['gnome-terminal', '--', 'gwc', '--chat-ui', '123']
    cmd_final = [term, flag] + args_gwc
    
    try:
        subprocess.Popen(cmd_final, start_new_session=True)
        return True
    except OSError as e:
        print(f"[X] Error lanzando terminal {term}: {e}")
        return False
