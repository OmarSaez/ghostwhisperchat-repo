# /usr/lib/ghostwhisperchat/datos/recursos.py
# Recursos estáticos: Colores, Textos, Constantes.

class Colores:
    # ANSI Color Codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Texto
    WHITE = "\033[97m"
    GREY = "\033[90m"
    BLACK = "\033[30m"
    
    # Sistema
    # --- SUPER PALETA 20 (v2.113) ---
    # Diseñada para máximo contraste en fondo negro
    
    # 1. Verdes
    C_GREEN_NEON  = "\033[38;5;46m"
    C_GREEN_LIME  = "\033[38;5;118m"
    C_OLIVE       = "\033[38;5;100m"
    
    # SYSTEM ALIASES (Backward Compatibility)
    GREEN   = C_GREEN_NEON
    RED     = "\033[38;5;196m" # C_RED_FIRE
    BLUE    = "\033[38;5;33m"  # C_BLUE_ROYAL
    YELLOW  = "\033[38;5;220m" # C_GOLD
    MAGENTA = "\033[38;5;201m" # C_MAGENTA
    CYAN    = "\033[38;5;51m"  # C_CYAN_ELEC
    
    # 2. Azules/Cyans
    
    # 2. Azules/Cyans
    C_BLUE_ROYAL  = "\033[38;5;33m" # Ajustado a 33 para legibilidad
    C_BLUE_ICE    = "\033[38;5;81m"
    C_CYAN_ELEC   = "\033[38;5;51m"
    C_TEAL_DARK   = "\033[38;5;30m"
    
    # 3. Rojos/Naranjas
    C_RED_FIRE    = "\033[38;5;196m"
    C_CORAL       = "\033[38;5;209m"
    C_ORANGE      = "\033[38;5;214m"
    
    # 4. Amarillos/Tierras
    C_GOLD        = "\033[38;5;220m"
    C_CREAM       = "\033[38;5;229m"
    C_BROWN       = "\033[38;5;130m" # Un poco mas rojizo para no ser invisible
    C_BEIGE       = "\033[38;5;137m"
    
    # 5. Rosas/Violetas
    C_PINK_HOT    = "\033[38;5;199m"
    C_PINK_PASTEL = "\033[38;5;218m"
    C_MAGENTA     = "\033[38;5;201m"
    C_PURPLE      = "\033[38;5;93m"
    C_LAVENDER    = "\033[38;5;147m"
    
    # 6. Neutro
    C_SILVER      = "\033[38;5;250m"

    NICK_COLORS = [
        C_GREEN_NEON, C_GREEN_LIME, C_OLIVE,
        C_BLUE_ROYAL, C_BLUE_ICE, C_CYAN_ELEC, C_TEAL_DARK,
        C_RED_FIRE, C_CORAL, C_ORANGE,
        C_GOLD, C_CREAM, C_BROWN, C_BEIGE,
        C_PINK_HOT, C_PINK_PASTEL, C_MAGENTA, C_PURPLE, C_LAVENDER,
        C_SILVER
    ]
    
    # Fondos (para resaltar menciones)
    # Style: GOLD PREMIUM (v2.113)
    BG_YELLOW = "\033[48;5;220m" # Gold
    BG_RED    = "\033[41m"       # Error standard
    BG_GREEN  = "\033[42m"       # Green for success
    
    # Texto High Contrast para fondos claros
    BLACK_TXT = "\033[38;5;0m"

# Versionado - Estable version con apodos, nombres reales, dashboard pro color, estados y @todos
APP_VER_NUM = "2.149.44"
APP_VER_TAG = "TEST2 - 'foto' Keyword Fix"
APP_VERSION = f"v{APP_VER_NUM} ({APP_VER_TAG})"

BANNER = r"""
Inicializando...

  ▄████  █     █░ ▄████▄  
 ██▒ ▀█▒▓█░ █ ░█░▒██▀ ▀█  
▒██░▄▄▄░▒█░ █ ░█ ▒▓█    ▄ 
░▓█  ██▓░█░ █ ░█ ▒▓▓▄ ▄██▒
░▒▓███▀▒░░██▒██▓ ▒ ▓███▀ ░
 ░▒   ▒ ░ ▓░▒ ▒  ░ ░▒ ▒  ░
  ░   ░   ▒ ░ ░    ░  ▒   
░ ░   ░   ░   ░  ░        
      ░     ░    ░ ░      
                 ░     2.0   
"""

AYUDA = f"""
{Colores.BLUE}{Colores.BOLD}========================================================================
   DICCIONARIO DE COMANDOS - GHOSTWHISPERCHAT {APP_VER_NUM}
========================================================================{Colores.RESET}

{Colores.MAGENTA}{Colores.BOLD}>> GESTIÓN DE CHATS{Colores.RESET}
  {Colores.GREEN}--dm <Nick/IP>{Colores.RESET} .............. Iniciar chat privado.
        {Colores.GREY}[Alias: -d, --mensaje, --susurrar]{Colores.RESET}

  {Colores.GREEN}--crearpublico <Nombre>{Colores.RESET} ...... Crear un grupo público (Sala).
        {Colores.GREY}[Alias: -o, --publico, --sala]{Colores.RESET}

  {Colores.GREEN}--crearprivado <Nom> <Pwd>{Colores.RESET} ... Crear un grupo privado con clave.
        {Colores.GREY}[Alias: -p, --privado, --candado]{Colores.RESET}

  {Colores.GREEN}--unirse <Nombre>{Colores.RESET} ............ Unirse a un grupo existente.
        {Colores.GREY}[Alias: -u, --entrar, --join]{Colores.RESET}

  {Colores.GREEN}--agregar <Nick>{Colores.RESET} ............. Invitar usuario al grupo actual.
        {Colores.GREY}[Alias: -a, --invitar, --meter]{Colores.RESET}

  {Colores.GREEN}--aceptar / --rechazar{Colores.RESET} ....... Responder a solicitudes pendientes.

  {Colores.GREEN}--salir{Colores.RESET} ...................... Salir del chat o cerrar sesión.
        {Colores.GREY}[Alias: -x, --chau, --exit]{Colores.RESET}

{Colores.MAGENTA}{Colores.BOLD}>> RED Y CONTACTOS{Colores.RESET}
  {Colores.GREEN}--enlinea{Colores.RESET} .................... Escanear red local (¿Quién está?).
        {Colores.GREY}[Alias: -s, --buscar, --radar]{Colores.RESET}

  {Colores.GREEN}--vergrupos{Colores.RESET} .................. Ver salas públicas disponibles.
        {Colores.GREY}[Alias: -g, --grupos, --salas]{Colores.RESET}

  {Colores.GREEN}--contactos{Colores.RESET} .................. Ver historial persistente de amigos.
        {Colores.GREY}[Alias: -c, --amigos]{Colores.RESET}

  {Colores.GREEN}--invisible{Colores.RESET} .................. {Colores.YELLOW}[Switch]{Colores.RESET} Ocultarse del radar.
        {Colores.GREY}[Alias: -v, --fantasma]{Colores.RESET}

{Colores.MAGENTA}{Colores.BOLD}>> UTILIDADES{Colores.RESET}
  {Colores.GREEN}--archivo <Ruta>{Colores.RESET} ............. Enviar archivo (Soporta Drag & Drop).
        {Colores.GREY}[Alias: -f, --enviar]{Colores.RESET}

  {Colores.GREEN}--imagen <Ruta>{Colores.RESET} .............. Enviar imagen visual (ASCII) y original.
        {Colores.GREY}[Alias: -i, --foto, --pic]{Colores.RESET}

  {Colores.GREEN}--cambiarnombre <Nuevo>{Colores.RESET} ....... Cambiar tu Nick actual.
        {Colores.GREY}[Alias: -n, --nick]{Colores.RESET}

  {Colores.GREEN}--estado <Texto>{Colores.RESET} .............. Publicar mensaje de estado.
        {Colores.GREY}[Alias: -e, --mood]{Colores.RESET}

  {Colores.GREEN}--info{Colores.RESET} ....................... Ver estado del sistema, IP y versión.
  {Colores.GREEN}--limpiar{Colores.RESET} .................... Limpiar pantalla.

{Colores.MAGENTA}{Colores.BOLD}>> SISTEMA{Colores.RESET}
  {Colores.GREEN}--log{Colores.RESET} ........................ {Colores.YELLOW}[Switch]{Colores.RESET} Guardar chat en archivo.
  {Colores.GREEN}--descarga{Colores.RESET} ................... {Colores.YELLOW}[Switch]{Colores.RESET} Auto-aceptar archivos.

{Colores.CYAN}Para ver la lista completa de alias, escribe:{Colores.RESET} {Colores.BOLD}--abreviaciones{Colores.RESET}
"""

# Mapeo de comandos para mostrar en --abreviaciones
ABBREVIATIONS_DISPLAY = {
    "GESTIÓN DE CHATS": {
        "MENSAJE PRIVADO": {
            'aliases': ['--dm', '-d', '--mensaje', '--susurrar', '--priv'],
            'desc': "Invitar a un chat privado a un usuario (Nick/IP)."
        },
        "CREAR SALA PÚBLICA": {
            'aliases': ['--crearpublico', '-o', '--publico', '--abrir', '--sala'],
            'desc': "Crear un grupo público visible para todos."
        },
        "CREAR SALA PRIVADA": {
            'aliases': ['--crearprivado', '-p', '--privado', '--candado', '--cerrado'],
            'desc': "Crear un grupo privado con contraseña."
        },
        "UNIRSE A SALA": {
            'aliases': ['--unirse', '-u', '--entrar', '--join'],
            'desc': "Entrar a un grupo público o privado."
        },
        "INVITAR AL GRUPO": {
            'aliases': ['--agregar', '-a', '--invitar', '--sumar', '--meter'],
            'desc': "Sumar usuarios conectados al grupo actual."
        },
        "ACEPTAR SOLICITUD": {
            'aliases': ['--aceptar'],
            'desc': "Confirmar una invitación entrante."
        },
        "RECHAZAR SOLICITUD": {
            'aliases': ['--rechazar'],
            'desc': "Denegar una invitación entrante."
        },
        "MODO SILENCIO": {
            'aliases': ['--silenciar', '-m', '--shh', '--nomolestar', '--mute'],
            'desc': "[Switch] Activar/Desactivar notificaciones."
        },
        "LISTAR ASISTENTES": {
            'aliases': ['--ls', '-l', '--gente', '--lista', '--usuarios'],
            'desc': "Ver quiénes están en el chat actual."
        },
        "SALIR / DESCONECTAR": {
            'aliases': ['--salir', '-x', '--chau', '--adios', '--exit'],
            'desc': "Cerrar sesión y salir del programa."
        }
    },

    "RED Y CONTACTOS": {
        "ESCANEAR RED": {
            'aliases': ['--enlinea', '-s', '--buscar', '--radar', '--quienes'],
            'desc': "Buscar usuarios activos en la red local."
        },
        "EXPLORAR GRUPOS": {
            'aliases': ['--vergrupos', '-g', '--grupos', '--explorar', '--salas'],
            'desc': "Listar grupos públicos disponibles."
        },
        "CONTACTOS CONOCIDOS": {
            'aliases': ['--contactos', '-c', '--amigos', '--agenda', '--historial'],
            'desc': "Ver listado de usuarios con los que hablaste."
        },
        "VISIBILIDAD EN RED": {
            'aliases': ['--invisible', '-v', '--fantasma', '--oculto', '--visibilidad'],
            'desc': "[Switch] Ocultarte o mostrarte en los escaneos de otros."
        }
    },

    "UTILIDADES Y ARCHIVOS": {
        "ENVIAR ARCHIVO": {
            'aliases': ['--archivo', '-f', '--enviar', '--mandar', '--adjuntar'],
            'desc': "Enviar un archivo a la sala actual (puedes arrastrarlo al chat para la ruta)."
        },
        "ENVIAR IMAGEN ASCII": {
            'aliases': ['--imagen', '-P', '--foto', '--picture', '-i'],
            'desc': "Mandar foto como Arte ASCII. Uso: --imagen <ruta> <opcional:ancho>"
        },
        "CAMBIAR NOMBRE": {
            'aliases': ['--cambiarnombre', '-n', '--nick', '--apodo', '--nombre'],
            'desc': "Cambiar tu nombre de usuario."
        },
        "CAMBIAR ESTADO": {
            'aliases': ['--estado', '-e', '--situacion', '--mood', '--st'],
            'desc': "Definir un mensaje de estado personal."
        },
        "INFO DEL SISTEMA": {
            'aliases': ['--estados-globales', '-i', '--info', '--config', '--todo'],
            'desc': "Ver IP, versión, configuración y logs."
        },
        "AYUDA GENERAL": {
            'aliases': ['--ayuda', '-?', '--help'],
            'desc': "Ver instrucciones generales y sintaxis."
        },
        "VER ABREVIACIONES": {
            'aliases': ['--abreviaciones', '-ab', '--alias'],
            'desc': "Mostrar este listado de comandos y variantes."
        },
        "LIMPIAR PANTALLA": {
            'aliases': ['--limpiar', '-k', '--borrar', '--cls', '--vaciar', '--clear'],
            'desc': "Limpiar el texto de la consola."
        }
    },

    "SISTEMA": {
        "GUARDAR HISTORIAL": {
            'aliases': ['--log', '-r', '--guardar', '--registro', '--grabar'],
            'desc': "[Switch] Guardar o no el historial de chat."
        },
        "DESCARGA AUTOMÁTICA": {
            'aliases': ['--descarga', '-b', '--bajar', '--autobajar', '--dl'],
            'desc': "[Switch] Aceptar archivos automáticamente o preguntar siempre."
        }
    }
}

COMMAND_MAP = {
    'CHAT':         ['--dm', '-d', '--mensaje', '--susurrar', '--priv'],
    'CREATE_PUB':   ['--crearpublico', '-o', '--publico', '--abrir', '--sala'],
    'CREATE_PRIV':  ['--crearprivado', '-p', '--privado', '--candado', '--cerrado'],
    'JOIN':         ['--unirse', '-u', '--entrar', '--join'],
    'ADD':          ['--agregar', '-a', '--invitar', '--sumar', '--meter'],
    'ACCEPT':       ['--aceptar'],
    'DENY':         ['--rechazar'],
    'MUTE_TOGGLE':  ['--silenciar', '-m', '--shh', '--nomolestar', '--mute'],
    'LS':           ['--ls', '-l', '--gente', '--lista', '--usuarios'],
    'EXIT':         ['--salir', '-x', '--chau', '--adios', '--exit'],
    'SCAN':             ['--enlinea', '-s', '--buscar', '--radar', '--quienes', '--scan'],
    'SCAN_RESULTS':     ['--scan-results', '--resultados-scan'],
    'LIST_GROUPS':      ['--vergrupos', '-g', '--grupos', '--explorar', '--salas'],
    'CONTACTS':         ['--contactos', '-c', '--amigos', '--agenda', '--historial', '--contacts'],
    'VISIBILITY_TOGGLE':['--invisible', '-v', '--fantasma', '--oculto', '--visibilidad'],
    'FILE':         ['--archivo', '-f', '--enviar', '--mandar', '--adjuntar'],
    'CHANGE_NICK':  ['--cambiarnombre', '-n', '--nick', '--apodo', '--nombre'],
    'STATUS':       ['--estado', '-e', '--situacion', '--mood', '--st'],
    'GLOBAL_STATUS':['--estados-globales', '-i', '--info', '--config', '--todo'],
    'HELP':         ['--ayuda', '-?', '--help'],
    'SHORTCUTS':    ['--abreviaciones', '-ab', '--alias'],
    'CLEAR':        ['--limpiar', '-k', '--borrar', '--cls', '--vaciar', '--clear'],
    'LOG_TOGGLE':   ['--log', '-r', '--guardar', '--registro', '--grabar'],
    'DL_TOGGLE':    ['--descarga', '-b', '--bajar', '--autobajar', '--dl'],
    'FILE':         ['--archivo', '-f', '--enviar', '--file'],
    'PHOTO_BG':     ['--foto-bg'] # Comando interno silencioso
}

import time
import sys

def mostrar_animacion_espera(mensaje="Procesando", segundos=1.2):
    """
    Muestra una animación 'g w c' personalizada con efecto de onda.
    """
    frames = [
        f"{Colores.YELLOW}[*] {mensaje} {Colores.GREEN}   {Colores.RESET}",
        f"{Colores.YELLOW}[*] {mensaje} {Colores.GREEN}g   {Colores.RESET}",
        f"{Colores.YELLOW}[*] {mensaje} {Colores.GREEN}gw  {Colores.RESET}",
        f"{Colores.YELLOW}[*] {mensaje} {Colores.GREEN}gwc {Colores.RESET}",
        f"{Colores.YELLOW}[*] {mensaje} {Colores.GREEN}   {Colores.RESET}",
        f"{Colores.YELLOW}[*] {mensaje} {Colores.GREEN}gwc {Colores.RESET}",
    ]
    
    # Calcular delay para que cícle al menos 2 veces o dure 'segundos'
    cycle_time = 0.4 # segs por frame
    total_frames = int(segundos / cycle_time)
    if total_frames < 3: total_frames = 6 # Minimo 2 ciclos
    
    for i in range(total_frames):
        frame = frames[i % len(frames)]
        sys.stdout.write(f"\r{frame}") # \r vuelve al inicio
        sys.stdout.flush()
        time.sleep(cycle_time)
    
    # Limpiar linea al final o dejarla? 
    # Mejor dejar el mensaje base limpio
    sys.stdout.write(f"\r{Colores.YELLOW}[*] {mensaje} {Colores.GREEN}Done!{Colores.RESET}\n")
    sys.stdout.flush()
