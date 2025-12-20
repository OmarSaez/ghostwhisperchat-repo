# utf-8
"""
RECURSOS ESTÁTICOS DE GHOSTWHISPERCHAT 2.0
Aquí se definen constantes visuales, textos y diccionarios estáticos.
No contiene lógica, solo datos.
"""

class Colores:
    """Paleta de colores ANSI para la terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    # Alias semánticos (para que el código sea legible)
    SISTEMA = CYAN
    ERROR = RED
    EXITO = GREEN
    ALERTA = YELLOW
    USUARIO = HEADER

# Definición centralizada de comandos y sus abreviaciones
# Formato: 'comando_estandar': ['alias1', 'alias2', ...]
ABREVIACIONES = {
    'ayuda':        ['--help', '-h', '?', '--?', 'ayuda'],
    'version':      ['--version', '-v', 'ver'],
    'salir':        ['--salir', 'salir', 'exit', 'quit', ':q'],
    'listar':       ['--ls', '-l', 'listar', 'list'],
    'scan':         ['--scan', '--quienes', '-q', 'who'],
    'unirse':       ['--join', '-j', 'unirse', '--chatgrupal', '--g'],
    'crear':        ['--create', '-c', 'crear'],
    'privado':      ['--priv', '-p', 'privado', '--chatpersonal'],
    'mensaje':      ['--msg', '-m', 'msg', 'enviar'],
    'nick':         ['--nick', '-n', 'nombre', '--name'],
    'estado':       ['--status', '-s', 'estado'],
    'update':       ['--update', '-u', 'actualizar', 'gwc update']
}

# Textos largos
BANNER = f"""{Colores.BOLD}{Colores.CYAN}
   GhostWhisperChat 2.0
   Arquitectura Modular
{Colores.END}"""

AYUDA_GENERAL = f"""
{Colores.BOLD}COMANDOS DISPONIBLES:{Colores.END}

  {Colores.GREEN}Conexión:{Colores.END}
    --join [ID] [CLAVE]    Unirse o crear un grupo. (Alias: --g)
    --priv [IP]            Iniciar chat privado.
    
  {Colores.GREEN}Utilidades:{Colores.END}
    --ls                   Ver miembros del chat actual.
    --scan                 Buscar gente en la red (UDP).
    --nick [NUEVO]         Cambiar tu nombre.
    
  {Colores.GREEN}Sistema:{Colores.END}
    --update               Actualizar software.
    --salir                Cerrar sesión.
"""
