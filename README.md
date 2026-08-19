
# GhostWhisperChat – Global & LAN P2P Chat

GhostWhisperChat (GWC) es un sistema de mensajería y transferencia descentralizado P2P con cifrado E2E, transferencia de archivos. Funciona tanto en **red local (LAN)** mediante descubrimiento automático como de forma **global (WAN)** a través de **Tor Onion Services v3** sin depender de servidores centrales.

## INSTALADOR

```bash
# 1. Agregar Clave GPG
wget -qO - https://omarsaez.github.io/ghostwhisperchat-repo/public.key | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/ghostwhisperchat.gpg > /dev/null

# 2. Agregar Repositorio
echo "deb https://omarsaez.github.io/ghostwhisperchat-repo/ stable main" | sudo tee /etc/apt/sources.list.d/ghostwhisperchat.list

# 3. Instalar
sudo apt update
sudo apt install ghostwhisperchat
```


## DESINSTALACIÓN

Para desinstalar completamente GhostWhisperChat y eliminar su repositorio de tu sistema, ejecuta los siguientes comandos en la terminal:

```bash
# 1. Desinstalar el programa (y sus archivos de configuración)
sudo apt remove --purge ghostwhisperchat -y

# 2. Eliminar el repositorio de la lista de fuentes
sudo rm /etc/apt/sources.list.d/ghostwhisperchat.list

# 3. Eliminar la clave GPG
sudo rm /etc/apt/trusted.gpg.d/ghostwhisperchat.gpg

# 4. Actualizar la lista de paquetes para reflejar los cambios
sudo apt update
```


## COMANDOS Y ABREVIACIONES

**GhostWhisperChat** cuenta con múltiples comandos y alias (abreviaciones) para hacer tu experiencia más rápida. 

⚠️ **IMPORTANTE: Cómo usar los comandos según dónde estés**
* **Fuera de un chat (en tu terminal de Linux):** Debes anteponer `gwc` antes del comando para que el sistema lo reconozca. 
  * *Ejemplo:* `gwc --enlinea`, `gwc --dm Kali114` o `gwc --dm abcdef...xyz.onion`
* **Dentro de una sala de chat:** Escribe el comando directamente (empezando con los guiones `--` o `-`). Si escribes `gwc` dentro de un chat, ¡se enviará como un mensaje de texto normal en lugar de ejecutarse!
  * *Ejemplo:* `--enlinea` o `--dm Kali114`

*Nota: Los comandos marcados como **[Switch]** funcionan como un interruptor; al ejecutarlos cambian entre activado o desactivado.*


### 💬 Gestión de Chats
| Comando Principal | Parámetros | Descripción | Alias Disponibles |
| :--- | :--- | :--- | :--- |
| `--dm` | `<Nick/IP/Onion>` | Iniciar chat privado con un usuario (LAN o WAN Global). | `-d`, `--mensaje`, `--susurrar`, `--priv` |
| `--crearpublico` | `<Nombre>` | Crear un grupo público visible para todos. | `-o`, `--publico`, `--abrir`, `--sala` |
| `--crearprivado` | `<Nom> <Pwd>` | Crear un grupo privado protegido con contraseña. | `-p`, `--privado`, `--candado`, `--cerrado` |
| `--unirse` | `<Nombre>` | Entrar a un grupo público o privado existente. | `-u`, `--entrar`, `--join` |
| `--agregar` | `<Nick/IP/Onion>` | Invitar a un usuario conectado al grupo actual. | `-a`, `--invitar`, `--sumar`, `--meter` |
| `--aceptar` | | Confirmar una invitación entrante. | |
| `--rechazar` | | Denegar una invitación entrante. | |
| `--silenciar` | | **[Switch]** Activar/Desactivar notificaciones. | `-m`, `--shh`, `--nomolestar`, `--mute` |
| `--ls` | | Ver quiénes están en el chat actual. | `-l`, `--gente`, `--lista`, `--usuarios` |
| `--salir` | | Salir del chat actual o cerrar sesión. | `-x`, `--chau`, `--adios`, `--exit` |

### 🌐 Identidad Global y Red WAN
| Comando Principal | Parámetros | Descripción | Alias Disponibles |
| :--- | :--- | :--- | :--- |
| `--mi-id` | | Consultar tu ID Global (.onion) para recibir mensajes de cualquier red. | `--onion`, `--id-global`, `--my-id` |
| `--enlinea` | | Escanear la red local buscando usuarios activos. | `-s`, `--buscar`, `--radar`, `--quienes`, `--scan` |
| `--vergrupos` | | Listar los grupos y salas públicas disponibles. | `-g`, `--grupos`, `--explorar`, `--salas` |
| `--contactos` | | Ver el historial de usuarios (LAN y WAN) con los que hablaste. | `-c`, `--amigos`, `--agenda`, `--historial`, `--contacts` |
| `--invisible` | | **[Switch]** Ocultarte de los escaneos de otros en la red. | `-v`, `--fantasma`, `--oculto`, `--visibilidad` |

### 📁 Utilidades y Archivos
| Comando Principal | Parámetros | Descripción | Alias Disponibles |
| :--- | :--- | :--- | :--- |
| `--archivo` | `<Ruta>` | Enviar un archivo (Soporta arrastrar y soltar). | `-f`, `--enviar`, `--mandar`, `--adjuntar`, `--file` |
| `--imagen` | `<Ruta> [ancho]` | Mandar foto como Arte ASCII y original (Soporta arrastrar y soltar). | `-i`, `-P`, `--foto`, `--picture` |
| `--cambiarnombre` | `<Nuevo>` | Cambiar tu Nick actual. | `-n`, `--nick`, `--apodo`, `--nombre` |
| `--estado` | `<Texto>` | Publicar un mensaje de estado personal. | `-e`, `--situacion`, `--mood`, `--st` |
| `--info` | | Ver estado del sistema, tu IP, ID Onion global, versión y logs. | `--estados-globales`, `-i`, `--config`, `--todo` |
| `--limpiar` | | Limpiar el texto de la consola. | `-k`, `--borrar`, `--cls`, `--vaciar`, `--clear` |
| `--ayuda` | | Ver menú de ayuda general en la app. | `-?`, `--help` |
| `--abreviaciones` | | Mostrar el listado de comandos dentro del chat. | `-ab`, `--alias` |

### ⚙️ Sistema
| Comando Principal | Parámetros | Descripción | Alias Disponibles |
| :--- | :--- | :--- | :--- |
| `--log` | | **[Switch]** Guardar o dejar de guardar el chat en un archivo. | `-r`, `--guardar`, `--registro`, `--grabar` |
| `--descarga` | | **[Switch]** Activa la aceptación automática de archivos. | `-b`, `--bajar`, `--autobajar`, `--dl` |
