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
    ("qterminal", "-e"), #Kali
    ("gnome-terminal", "--"), #Ubuntu
    ("mate-terminal", "--"), #Parrot
    ("xfce4-terminal", "--execute"), 
    ("konsole", "-e"),
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

def abrir_chat_ui(id_destino, nombre_legible=None, es_grupo=False, env_vars=None):
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
    
    # Preparar Entorno Dinamico (Display Injection)
    final_env = os.environ.copy()
    if env_vars:
        log_launcher(f"[LAUNCHER] Env Injection: {env_vars}")
        final_env.update(env_vars)
        
    log_launcher(f"[LAUNCHER] Entorno Efectivo (DISPLAY): {final_env.get('DISPLAY', 'UNK')}")

    for term, flag in TERMINALES:
        if shutil.which(term):
            # Construir comando final
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
                # Konsole, QTerminal, Xterm, Kitty need a shell to parse the command string
                # We wrap it in sh -c to be safe and universal
                args_term.append(flag)
                
                # IMPORTANT: We use sh -c to execute the python string
                # INJECT TITLE: printf "\033]0;TITLE\007" sets window title in xterm-compatible terms
                safe_title = full_title.replace("'", "").replace('"', '') # Sanitation
                wrapped_cmd = f"sh -c 'printf \"\\033]0;{safe_title}\\007\"; {cmd_inner_str}'"
                args_term.append(wrapped_cmd)
            else:
                # Fallback
                args_term.append(flag)
                args_term.extend(inner_args)
            
            log_launcher(f"[LAUNCHER] Intentando terminal: {term}")
            log_launcher(f"[LAUNCHER] Exec args: {args_term}")
            
            try:
                subprocess.Popen(args_term, start_new_session=True, env=final_env)
                log_launcher(f"[LAUNCHER] Éxito lanzando {term}")
                return True
            except Exception as e:
                log_launcher(f"[LAUNCHER] Error lanzando {term}: {e}")
                continue
                
    log_launcher("[LAUNCHER] No se encontró terminal compatible.")
    return False

