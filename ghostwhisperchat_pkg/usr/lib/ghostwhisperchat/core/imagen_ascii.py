import sys
import os

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def render_ascii(image_path, width=60):
    """
    Convierte una imagen a ASCII Art (Half-Block ANSI).
    Rango width: 10 - 190. Clamp automatico.
    Retorna string multilinea (con \n).
    """
    if not PIL_AVAILABLE:
        return "ERROR: Libreria 'Pillow' no instalada. Instale con: sudo apt install python3-pil"

    if not os.path.exists(image_path):
        return f"ERROR: Archivo no encontrado: {image_path}"

    # Clamping
    try:
        width = int(width)
    except ValueError:
        width = 60
        
    width = max(10, min(width, 190))

    try:
        img = Image.open(image_path)
    except Exception as e:
        return f"ERROR: No se pudo abrir la imagen. {str(e)}"

    # Algoritmo V1 (Half-Block)
    aspect_ratio = img.height / img.width
    new_height = int(width * aspect_ratio) 
    if new_height % 2 != 0: new_height += 1
    
    img = img.resize((width, new_height), Image.Resampling.LANCZOS)
    img = img.convert('RGB')
    pixels = img.load()
    
    res = ""
    for y in range(0, new_height, 2):
        for x in range(width):
            r1, g1, b1 = pixels[x, y]
            if y+1 < new_height: r2, g2, b2 = pixels[x, y+1]
            else: r2, g2, b2 = 0,0,0
            
            res += f"\033[38;2;{r1};{g1};{b1}m\033[48;2;{r2};{g2};{b2}m▀"
        res += "\033[0m\n"
        
    return res
