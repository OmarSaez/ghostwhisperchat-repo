# /usr/lib/ghostwhisperchat/core/launcher.py
# Lanzador de Terminales Agnostico (v2.1)

import shutil
import subprocess
import os

# Lista PRIORIZADA de terminales soportados
# (binario, flag_ejecucion)
TERMINALES = [
    ("gnome-terminal", "--"),
    ("mate-terminal", "--"),
    ("xfce4-terminal", "--execute"), 
    ("konsole", "-e"),
    ("tilix", "-e"),
    ("terminator", "-x"),
    ("xterm", "-e"),
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
    # Construir el comando del hijo
    # NOTA: Usamos sys.executable para garantizar que usamos el mismo python
    # Y escapamos los argumentos correctamente
    cmd_inner = f"{sys.executable} -m ghostwhisperchat.cliente --chat-ui {id_destino}"
    if es_grupo:
        cmd_inner += " --group"
        
    log_launcher(f"[LAUNCHER] Solicitud abrir UI: ID={id_destino}, GRUPO={es_grupo}")
    log_launcher(f"[LAUNCHER] Comando interno: {cmd_inner}")

    for term, flag in TERMINALES:
        if shutil.which(term):
            # Construir comando final
            # Ej: gnome-terminal -- /usr/bin/python3 -m ghostwhisperchat.cliente ...
            
            # Algunos terminales (gnome-terminal) usan --title
            args_term = [term]
            if term == "gnome-terminal":
                 args_term.extend(["--title", f"Chat GWC: {id_destino}"])
            
            args_term.append(flag)
            # shlex.split del inner command para pasarlo como lista de argumentos al exec
            args_term.extend(shlex.split(cmd_inner))
            
            log_launcher(f"[LAUNCHER] Intentando terminal: {term}")
            log_launcher(f"[LAUNCHER] Exec args: {args_term}")
            
            try:
                subprocess.Popen(args_term, start_new_session=True) # Added start_new_session for consistency with original
                log_launcher(f"[LAUNCHER] Éxito lanzando {term}")
                return True
            except Exception as e:
                log_launcher(f"[LAUNCHER] Error lanzando {term}: {e}")
                continue
                
    log_launcher("[LAUNCHER] No se encontró terminal compatible.")
    return False
