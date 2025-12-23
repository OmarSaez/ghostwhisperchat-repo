import shutil
import subprocess
import os
import sys
import shlex

# LOGGING SIMPLE (DEBUG)
def log_launcher(msg):
    try:
        with open("/tmp/gwc_launcher.log", "a") as f:
            f.write(f"{msg}\n")
    except:
        pass

# Lista PRIORIZADA de terminales soportados
# (binario, flag_ejecucion)
TERMINALES = [
    ("gnome-terminal", "--"),
    ("mate-terminal", "--"),
    ("xfce4-terminal", "--execute"), 
    ("konsole", "-e"),
    ("qterminal", "-e"),
    ("lxterminal", "-e"),
    ("kitty", "-e"), # Modern / GPU
    ("alacritty", "-e"), # Modern / Rust
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

def abrir_chat_ui(id_destino, nombre_legible=None, es_grupo=False):
    """
    Abre una nueva ventana de terminal ejecutando el modo UI del cliente.
    Ejecuta: gwc --chat-ui <ID>
    """
    
    # Construir el comando del hijo
    # Usamos sys.executable para apuntar al mismo intérprete Python
    cmd_inner_str = f"{sys.executable} -m ghostwhisperchat.cliente --chat-ui {id_destino}"
    if es_grupo:
        cmd_inner_str += " --group"
    
    # Dividir comando interno en lista argumentos seguros
    inner_args = shlex.split(cmd_inner_str)
        
    log_launcher(f"[LAUNCHER] Solicitud abrir UI: ID={id_destino}, GRUPO={es_grupo}")
    log_launcher(f"[LAUNCHER] Entorno (DISPLAY): {os.environ.get('DISPLAY', 'NO_DISPLAY')}")
    log_launcher(f"[LAUNCHER] Entorno (XDG_RUNTIME_DIR): {os.environ.get('XDG_RUNTIME_DIR', '?')}")
    log_launcher(f"[LAUNCHER] Comando interno raw: {cmd_inner_str}")

    for term, flag in TERMINALES:
        if shutil.which(term):
            # Construir comando final
            # Ej: ['gnome-terminal', '--title', '...', '--', 'python3', '-m', ...]
            
            args_term = [term]
            
             # Flags específicos de terminal (Titulo Personalizado)
            display_title = nombre_legible if nombre_legible else id_destino[:8]
            prefix = "Chat Grupo" if es_grupo else "Chat Priv"
            full_title = f"{prefix}: {display_title}"
            
            if term in ["gnome-terminal", "mate-terminal", "xfce4-terminal"]:
                 args_term.extend(["--title", full_title])
            
            # Flag de ejecución ("--" o "-e" o "-x")
            
            if flag == "--":
                # Gnome/Mate/XFCE support separate arguments after --
                args_term.append(flag)
                args_term.extend(inner_args)
            elif flag == "-e" or flag == "-x":
                # Konsole, QTerminal, Xterm, Kitty often prefer single string for -e
                # Also wrapping in sh to ensure path resolution
                args_term.append(flag)
                # Pass whole command as one string
                args_term.append(cmd_inner_str)
            else:
                # Fallback
                args_term.append(flag)
                args_term.extend(inner_args)
            
            log_launcher(f"[LAUNCHER] Intentando terminal: {term}")
            log_launcher(f"[LAUNCHER] Exec args: {args_term}")
            
            try:
                subprocess.Popen(args_term, start_new_session=True)
                log_launcher(f"[LAUNCHER] Éxito lanzando {term}")
                return True
            except Exception as e:
                log_launcher(f"[LAUNCHER] Error lanzando {term}: {e}")
                continue
                
    log_launcher("[LAUNCHER] No se encontró terminal compatible.")
    return False

