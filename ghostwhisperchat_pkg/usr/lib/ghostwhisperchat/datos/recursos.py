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
    RED = "\033[91m"      # Errores [X]
    GREEN = "\033[92m"    # Éxitos [+]
    YELLOW = "\033[93m"   # Alerta [-] / Menciones
    BLUE = "\033[94m"     # Info temporal [*] / Barras
    
    # Fondos (para resaltar menciones)
    BG_YELLOW = "\033[43m"
    BG_RED = "\033[41m"

# Versionado
APP_VER_NUM = "2.29"
APP_VER_TAG = "Todos los comandos!"
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
                 ░        

:: v2 :: LAN Distributed Chat ::
"""

AYUDA = """
=========================================================================
DICCIONARIO DE COMANDOS - GHOSTWHISPERCHAT 2.0
=========================================================================

GESTIÓN DE CHATS:
  --dm (Nick/IP)                : Iniciar chat privado.
                          Alias: -d, --mensaje, --susurrar
  --crearpublico (Nombre)       : Crear un grupo público.
                          Alias: -o, --publico, --sala
  --crearprivado (Nombre Clave) : Crear un grupo privado (requiere clave).
                          Alias: -p, --privado, --candado
  --unirse (Nombre)             : Unirse a un grupo.
                          Alias: -u, --entrar, --join
  --agregar (Nicks)             : Invitar usuarios al grupo actual.
                          Alias: -a, --invitar, --meter
  --aceptar / --rechazar        : Responder a solicitudes.
  --salir                       : Salir del chat o cerrar sesión.
                          Alias: -x, --chau, --exit

RED Y CONTACTOS:
  --enlinea                     : Escanear red (¿Quién está online?).
                          Alias: -s, --buscar, --radar
  --vergrupos                   : Ver grupos públicos disponibles.
                          Alias: -g, --grupos, --salas
  --contactos                   : Ver historial de usuarios.
                          Alias: -c, --amigos
  --invisible                   : Ocultarse del escáner (Switch).
                          Alias: -v, --fantasma

UTILIDADES:
  --archivo (Ruta)              : Enviar archivo (Drag & Drop soportado).
                          Alias: -f, --enviar
  --cambiarnombre               : Cambiar tu nick.
                          Alias: -n, --nick
  --estado (Texto)              : Poner un mensaje de estado.
                          Alias: -e, --mood
  --info                        : Ver estado del sistema e IP.
  --limpiar                     : Limpiar pantalla.
                          Alias: --cls, --clear

SISTEMA:
  --log                         : Guardar historial (Switch).
  --descarga                    : Descarga automática de archivos (Switch).

Para ver todos los alias, escribe: --abreviaciones
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
    'DM':           ['--dm', '-d', '--mensaje', '--susurrar', '--priv'],
    'CREATE_PUB':   ['--crearpublico', '-o', '--publico', '--abrir', '--sala'],
    'CREATE_PRIV':  ['--crearprivado', '-p', '--privado', '--candado', '--cerrado'],
    'JOIN':         ['--unirse', '-u', '--entrar', '--join'],
    'ADD':          ['--agregar', '-a', '--invitar', '--sumar', '--meter'],
    'ACCEPT':       ['--aceptar'],
    'DENY':         ['--rechazar'],
    'MUTE_TOGGLE':  ['--silenciar', '-m', '--shh', '--nomolestar', '--mute'],
    'LS':           ['--ls', '-l', '--gente', '--lista', '--usuarios'],
    'EXIT':         ['--salir', '-x', '--chau', '--adios', '--exit'],
    'SCAN':             ['--enlinea', '-s', '--buscar', '--radar', '--quienes'],
    'LIST_GROUPS':      ['--vergrupos', '-g', '--grupos', '--explorar', '--salas'],
    'CONTACTS':         ['--contactos', '-c', '--amigos', '--agenda', '--historial'],
    'VISIBILITY_TOGGLE':['--invisible', '-v', '--fantasma', '--oculto', '--visibilidad'],
    'FILE':         ['--archivo', '-f', '--enviar', '--mandar', '--adjuntar'],
    'CHANGE_NICK':  ['--cambiarnombre', '-n', '--nick', '--apodo', '--nombre'],
    'STATUS':       ['--estado', '-e', '--situacion', '--mood', '--st'],
    'GLOBAL_STATUS':['--estados-globales', '-i', '--info', '--config', '--todo'],
    'HELP':         ['--ayuda', '-?', '--help'],
    'SHORTCUTS':    ['--abreviaciones', '-ab', '--alias'],
    'CLEAR':        ['--limpiar', '-k', '--borrar', '--cls', '--vaciar', '--clear'],
    'LOG_TOGGLE':   ['--log', '-r', '--guardar', '--registro', '--grabar'],
    'DL_TOGGLE':    ['--descarga', '-b', '--bajar', '--autobajar', '--dl']
}
