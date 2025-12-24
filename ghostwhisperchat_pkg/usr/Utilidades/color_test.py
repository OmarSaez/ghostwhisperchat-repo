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
BOLD          = "\033[1m"
GREY          = "\033[90m"

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

print("\n=== GALERÍA DE MENCIÓNES ===")
# Resumido
demo_mencion("5. GOLD (Premium)", "\033[48;5;220m", "\033[38;5;0m", bold=True)


print("\n" + "="*60)
print(f"{C_BLUE_ROYAL}{BOLD}   PROPUESTAS DE VISUALIZACIÓN DE IDENTIDAD (CMD --ls){RESET}")
print("="*60 + "\n")

# Datos Mock
nick_a = "Jualitungo"
real_a = "jose"
ip_a   = "192.168.1.234"

nick_b = "SuperParrot"
real_b = "omar"
ip_b   = "192.168.1.10"

def print_row(op_name, content):
    print(f"{C_GOLD}>> {op_name}:{RESET}")
    print(content)
    print("")

# --- OPCION 1 ---
line_1 = f" - {C_GREEN_NEON}{nick_a}{RESET} ({GREY}@{real_a}{RESET}) - {GREY}{ip_a}{RESET} [ONLINE]"
print_row("OPCIÓN 1: Estilo 'Social Handle' (@usuario)", line_1)

# --- OPCION 2 ---
line_2 = f" - {C_GREEN_NEON}{nick_a}{RESET} <{GREY}sys: {real_a}{RESET}> ({GREY}{ip_a}{RESET}) [ONLINE]"
print_row("OPCIÓN 2: Estilo 'System Source' (Hacker)", line_2)

# --- OPCION 3 ---
line_3 = f" - {C_GREEN_NEON}{nick_a}{RESET} [{GREY}{real_a}@{ip_a}{RESET}] [ONLINE]"
print_row("OPCIÓN 3: Estilo 'Identidad Combinada' (Compacto)", line_3)

# --- OPCION 4 ---
line_4 = f" - {C_GREEN_NEON}{nick_a}{RESET} ➜ {GREY}{real_a}{RESET} ({GREY}{ip_a}{RESET}) [ONLINE]"
print_row("OPCIÓN 4: Estilo 'Flecha de Verdad'", line_4)

# --- OPCION 5 ---
line_5 = f" - {C_GREEN_NEON}{nick_a:<12}{RESET} | {GREY}{real_a:<8}{RESET} | {GREY}{ip_a}{RESET} [ONLINE]"
print_row("OPCIÓN 5: Estilo 'Tubería' (Columnas)", line_5)