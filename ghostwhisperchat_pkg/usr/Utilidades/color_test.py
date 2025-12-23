import sys

# Tus constantes de color
C_GREEN_NEON  = "\033[38;5;46m"
C_GREEN_LIME  = "\033[38;5;118m"
C_OLIVE       = "\033[38;5;100m"
C_BLUE_ROYAL  = "\033[38;5;33m"
C_BLUE_ICE    = "\033[38;5;81m"
C_CYAN_ELEC   = "\033[38;5;51m"
C_TEAL_DARK   = "\033[38;5;30m"
C_RED_FIRE    = "\033[38;5;196m"
C_CORAL       = "\033[38;5;209m"
C_ORANGE      = "\033[38;5;214m"
C_GOLD        = "\033[38;5;220m"
C_CREAM       = "\033[38;5;229m"
C_BROWN       = "\033[38;5;130m"
C_BEIGE       = "\033[38;5;137m"
C_PINK_HOT    = "\033[38;5;199m"
C_PINK_PASTEL = "\033[38;5;218m"
C_MAGENTA     = "\033[38;5;201m"
C_PURPLE      = "\033[38;5;93m"
C_LAVENDER    = "\033[38;5;147m"
C_SILVER      = "\033[38;5;250m"
RESET         = "\033[0m"

COLORES = {
    "GREEN_NEON": C_GREEN_NEON, "GREEN_LIME": C_GREEN_LIME, "OLIVE": C_OLIVE,
    "BLUE_ROYAL": C_BLUE_ROYAL, "BLUE_ICE": C_BLUE_ICE, "CYAN_ELEC": C_CYAN_ELEC,
    "TEAL_DARK": C_TEAL_DARK, "RED_FIRE": C_RED_FIRE, "CORAL": C_CORAL,
    "ORANGE": C_ORANGE, "GOLD": C_GOLD, "CREAM": C_CREAM, "BROWN": C_BROWN,
    "BEIGE": C_BEIGE, "PINK_HOT": C_PINK_HOT, "PINK_PASTEL": C_PINK_PASTEL,
    "MAGENTA": C_MAGENTA, "PURPLE": C_PURPLE, "LAVENDER": C_LAVENDER,
    "SILVER": C_SILVER
}

print(f"\n{'NOMBRE DEL COLOR':<15} | {'VISTA PREVIA DEL NICK':<25}")
print("-" * 45)

for nombre, codigo in COLORES.items():
    # Simulamos un formato de chat: <Nick> Mensaje
    print(f"{nombre:<15} | {codigo}User_Test{RESET}: Hola, ¿cómo se ve este color?")

print("-" * 45)

# --- PRUEBA DE ESTILOS DE MENCIÓN (Visual Tuning) ---

def demo_mencion(nombre_estilo, bg_code, fg_code, bold=False):
    b = "\033[1m" if bold else ""
    reset = "\033[0m"
    print(f"\nEstilo {nombre_estilo}:")
    print(f"{bg_code}{fg_code}{b} __MENTION__ (Admin): @todos Reunión urgente en 5 min! {reset}")

print("\n=== GALERÍA DE ESTILOS DE MENCIÓN ===")

# V0: Original (Legacy - 16 colors) -> Lo que tenías antes
demo_mencion("0. ORIGINAL (Legacy 4-bit)", "\033[43m", "\033[30m", bold=False)

# V1: Resaltador Texto (Amarillo Neón 226)
# Fondo: 226 (Amarillo puro), Texto: 0 (Negro), Bold
demo_mencion("1. HIGH-VIS (Resaltador)", "\033[48;5;226m", "\033[38;5;0m", bold=True)

# V2: Alerta Roja (Rojo 196)
# Fondo: 196 (Rojo Fuego), Texto: 231 (Blanco Puro), Bold
demo_mencion("2. RED ALERT (Emergencia)", "\033[48;5;196m", "\033[38;5;231m", bold=True)

# V3: Cyberpunk (Cyan 51)
# Fondo: 51 (Cyan Eléctrico), Texto: 0 (Negro), Bold
demo_mencion("3. CYBER (Futurista)", "\033[48;5;51m", "\033[38;5;0m", bold=True)

# V4: Elegancia (Blanco 255)
# Fondo: 255 (Blanco Nieve), Texto: 0 (Negro), Bold
demo_mencion("4. ELEGANT (Alto Contraste)", "\033[48;5;255m", "\033[38;5;0m", bold=True)

# V5: Gold Standard (Oro 220)
# Fondo: 220 (Oro), Texto: 0 (Negro), Bold
demo_mencion("5. GOLD (Premium)", "\033[48;5;220m", "\033[38;5;0m", bold=True)

print("-" * 45)