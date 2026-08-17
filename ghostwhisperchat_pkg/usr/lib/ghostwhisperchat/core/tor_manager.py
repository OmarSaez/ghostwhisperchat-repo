# /usr/lib/ghostwhisperchat/core/tor_manager.py
# Gestor del Ciclo de Vida de Tor (WAN Overlay Network)

import os
import sys
import time
import shutil
import subprocess

TOR_CONFIG_DIR = os.path.expanduser("~/.ghostwhisperchat/tor")
ONION_KEY_FILE = os.path.expanduser("~/.ghostwhisperchat/onion_key")

class TorManager:
    """
    Gestiona el servicio oculto Tor Onion v3 para GhostWhisperChat.
    Permite obtener una identidad global (.onion) permanente y enrutar
    tráfico P2P a través de la red descentralizada de Tor.
    """
    def __init__(self, port_priv=44494, port_group=44496):
        self.port_priv = port_priv
        self.port_group = port_group
        
        self.onion_address = None
        self.socks_host = "127.0.0.1"
        self.socks_port = 9050
        self.control_port = 9051
        
        self.controller = None
        self.tor_process = None
        self.is_active = False
        self.status_message = "No iniciado"

    def iniciar(self):
        """
        Inicializa Tor intentando conectar al servicio del sistema o
        lanzando una instancia ligera en espacio de usuario.
        """
        try:
            import stem
            from stem.control import Controller
        except ImportError:
            self.status_message = "Librería python3-stem no disponible (Modo Solo LAN)"
            print(f"[*] TorManager: {self.status_message}", file=sys.stderr)
            return False

        # 1. Verificar si el binario de Tor existe en PATH o rutas estándar
        self.tor_binary = shutil.which("tor") or (
            "/usr/sbin/tor" if os.path.exists("/usr/sbin/tor") else (
                "/usr/bin/tor" if os.path.exists("/usr/bin/tor") else None
            )
        )
        if not self.tor_binary:
            self.status_message = "Binario 'tor' no encontrado en el sistema (Modo Solo LAN)"
            print(f"[*] TorManager: {self.status_message}", file=sys.stderr)
            return False

        os.makedirs(TOR_CONFIG_DIR, mode=0o700, exist_ok=True)
        self.status_message = "Conectando a la red Tor..."

        # 2. Intentar conectar a Tor ya corriendo (ControlPort 9051)
        conectado = self._conectar_controlador_existente()

        # 3. Si no se pudo conectar, intentar lanzar instancia Tor de usuario
        if not conectado:
            conectado = self._lanzar_tor_usuario()

        if not conectado or not self.controller:
            self.status_message = "No se pudo establecer conexión con el puerto de control de Tor"
            print(f"[!] TorManager: {self.status_message}", file=sys.stderr)
            return False

        # 4. Crear o recuperar el servicio oculto Onion v3
        return self._crear_servicio_oculto()

    def _conectar_controlador_existente(self):
        """Intenta conectar y autenticar con un daemon Tor existente en 9051."""
        try:
            from stem.control import Controller
            controller = Controller.from_port(address="127.0.0.1", port=self.control_port)
            controller.authenticate()
            self.controller = controller
            print("[*] TorManager: Conectado al demonio Tor del sistema (Puerto 9051).", file=sys.stderr)
            return True
        except Exception as e:
            # Fallback: intentar socket unix por defecto en Debian
            try:
                from stem.control import Controller
                if os.path.exists("/run/tor/control"):
                    controller = Controller.from_socket_file("/run/tor/control")
                    controller.authenticate()
                    self.controller = controller
                    print("[*] TorManager: Conectado a Tor vía socket Unix (/run/tor/control).", file=sys.stderr)
                    return True
            except Exception:
                pass
            return False

    def _lanzar_tor_usuario(self):
        """Lanza una instancia de Tor ligera y dedicada para GWC."""
        try:
            import stem.process
            data_dir = os.path.join(TOR_CONFIG_DIR, "data")
            os.makedirs(data_dir, mode=0o700, exist_ok=True)

            print("[*] TorManager: Levantando proceso Tor en espacio de usuario...", file=sys.stderr)
            self.status_message = "Iniciando circuitos Tor..."
            
            # Buscar puertos libres para SOCKS y Control
            self.socks_port = 9055
            self.control_port = 9056

            tor_config = {
                'DataDirectory': data_dir,
                'SocksPort': str(self.socks_port),
                'ControlPort': str(self.control_port),
                'CookieAuthentication': '1'
            }

            def log_bootstrap(line):
                if "Bootstrapped" in line:
                    try:
                        pct = line.split("Bootstrapped")[1].split("%")[0].strip()
                        self.status_message = f"Conectando a la red Tor ({pct}%)..."
                    except Exception:
                        pass

            self.tor_process = stem.process.launch_tor_with_config(
                config=tor_config,
                tor_cmd=self.tor_binary,
                init_msg_handler=log_bootstrap,
                timeout=90,
                take_ownership=True
            )

            from stem.control import Controller
            controller = Controller.from_port(address="127.0.0.1", port=self.control_port)
            controller.authenticate()
            self.controller = controller
            print(f"[*] TorManager: Proceso Tor de usuario activo (SOCKS:{self.socks_port}, Control:{self.control_port}).", file=sys.stderr)
            return True
        except Exception as e:
            print(f"[!] TorManager: Error al lanzar instancia Tor: {e}", file=sys.stderr)
            return False

    def _crear_servicio_oculto(self):
        """Crea o carga el servicio efímero Onion v3 con llave persistente."""
        try:
            key_content = None
            key_type = "NEW"
            
            # Leer llave privada persistente si existe
            if os.path.exists(ONION_KEY_FILE):
                try:
                    with open(ONION_KEY_FILE, "r") as f:
                        key_content = f.read().strip()
                    if key_content:
                        key_type = "ED25519-V3"
                except Exception as e:
                    print(f"[!] Error leyendo {ONION_KEY_FILE}: {e}", file=sys.stderr)
                    key_content = None
                    key_type = "NEW"

            # Redireccionar puerto virtual 44494 a real_port_priv y 44496 a real_port_group
            ports_map = {
                44494: f"127.0.0.1:{self.port_priv}",
                44496: f"127.0.0.1:{self.port_group}"
            }

            if key_content:
                res = self.controller.create_ephemeral_hidden_service(
                    ports_map,
                    key_type=key_type,
                    key_content=key_content,
                    await_publication=False
                )
            else:
                res = self.controller.create_ephemeral_hidden_service(
                    ports_map,
                    key_type="NEW",
                    key_content="ED25519-V3",
                    await_publication=False
                )
                # Persistir la nueva llave privada generada
                if hasattr(res, 'private_key') and res.private_key:
                    try:
                        with open(ONION_KEY_FILE, "w") as f:
                            f.write(res.private_key)
                        os.chmod(ONION_KEY_FILE, 0o600)
                    except Exception as e:
                        print(f"[!] Error guardando llave en {ONION_KEY_FILE}: {e}", file=sys.stderr)

            self.onion_address = f"{res.service_id}.onion"
            self.is_active = True
            self.status_message = f"Conectado ({self.onion_address})"
            print(f"[*] TorManager: GWC-ID Global activo -> {self.onion_address}", file=sys.stderr)
            return True

        except Exception as e:
            self.status_message = f"Error creando servicio Onion: {e}"
            print(f"[X] TorManager: {self.status_message}", file=sys.stderr)
            return False

    def detener(self):
        """Detiene el servicio y cierra conexiones."""
        if self.controller:
            try:
                self.controller.close()
            except Exception:
                pass
            self.controller = None

        if self.tor_process:
            try:
                self.tor_process.terminate()
            except Exception:
                pass
            self.tor_process = None

        self.is_active = False
        self.status_message = "Detenido"
