# /usr/lib/ghostwhisperchat/core/transporte.py
# Capa de Transporte (Sockets UDP/TCP)

import socket
import select
import sys
import errno
from ghostwhisperchat.core.utilidades import get_local_ip

# Constantes de Puerto
PORT_PRIVATE = 44494   # TCP P2P
PORT_DISCOVERY = 44495 # UDP Broadcast
PORT_GROUP = 44496     # TCP Mesh

import threading

class GestorRed:
    def __init__(self):
        self.sock_udp = None       # 44495
        self.sock_tcp_group = None # 44496 (Listen)
        self.sock_tcp_priv = None  # 44494 (Listen)
        
        self.socks_host = "127.0.0.1"
        self.socks_port = 9050
        
        self.tcp_connections = []  # Lista de sockets TCP activos (conectados o aceptados)
        self.inputs = []           # Lista para select()
        
        # --- Pool de conexiones Tor persistentes ---
        # Clave: (host_onion, port) | Valor: socket vivo
        # Evita crear un circuito nuevo por cada mensaje (el mayor costo de latencia Tor).
        # Thread-safe via _pool_lock.
        self._onion_pool = {}          # { (host, port): socket }
        self._pool_lock = threading.Lock()

    def set_socks_proxy(self, host="127.0.0.1", port=9050):
        """Configura los parámetros del proxy SOCKS5 local para Tor"""
        self.socks_host = host
        self.socks_port = port

    def _conectar_socks5(self, host, port, timeout=40.0):
        """
        Establece una conexión TCP hacia un host .onion a través del proxy SOCKS5 local de Tor.
        Implementación estándar en Python socket puro (sin dependencias externas).
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((self.socks_host, self.socks_port))

        # 1. Saludo SOCKS5 (Autenticación no requerida: \x05\x01\x00)
        s.sendall(b"\x05\x01\x00")
        resp = s.recv(2)
        if len(resp) < 2 or resp[0] != 0x05 or resp[1] != 0x00:
            s.close()
            raise OSError("Fallo de negociación SOCKS5 con Tor")

        # 2. Petición CONNECT hacia dominio (.onion) -> ATYP 0x03
        host_bytes = host.encode('ascii')
        port_bytes = int(port).to_bytes(2, byteorder='big')
        req = bytes([0x05, 0x01, 0x00, 0x03, len(host_bytes)]) + host_bytes + port_bytes
        s.sendall(req)

        resp = s.recv(4)
        if len(resp) < 4 or resp[0] != 0x05 or resp[1] != 0x00:
            rep_code = resp[1] if len(resp) > 1 else -1
            s.close()
            raise OSError(f"Tor SOCKS5 no pudo conectar con {host}:{port} (Código: {rep_code})")

        # Drenar encabezado de dirección de respuesta SOCKS5
        atyp = resp[3]
        if atyp == 0x01:   # IPv4
            s.recv(4 + 2)
        elif atyp == 0x03: # Dominio
            dlen = s.recv(1)[0]
            s.recv(dlen + 2)
        elif atyp == 0x04: # IPv6
            s.recv(16 + 2)

        return s

    def iniciar_servidores(self):
        """Levanta los 3 sockets principales en modo escucha, buscando puertos libres."""
        try:
            # 1. UDP Discovery (Fixed Port 44495)
            self.sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                # Allow multiple instances to share UDP port for listening
                if hasattr(socket, "SO_REUSEPORT"):
                    self.sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except: pass
            
            self.sock_udp.bind(('0.0.0.0', PORT_DISCOVERY))
            self.sock_udp.setblocking(False)
            
            # Helper to find free port
            def bind_socket_range(base_port, max_attempts=10):
                for i in range(max_attempts):
                    port = base_port + i
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    try:
                        sock.bind(('0.0.0.0', port))
                        sock.listen(10)
                        sock.setblocking(False)
                        return sock, port
                    except OSError as e:
                        sock.close()
                        if e.errno == errno.EADDRINUSE: continue
                        raise e
                raise OSError(f"No free ports available starting from {base_port}")

            # 2. TCP Groups (Searching 44496+)
            self.sock_tcp_group, self.real_port_group = bind_socket_range(PORT_GROUP)
            
            # 3. TCP Private (Searching 44494)
            self.sock_tcp_priv, self.real_port_priv = bind_socket_range(PORT_PRIVATE)
            
            # Preparar inputs para select
            self.inputs = [self.sock_udp, self.sock_tcp_group, self.sock_tcp_priv]
            
            print(f"[*] Transportes iniciados: UDP:{PORT_DISCOVERY}, TCP_G:{self.real_port_group}, TCP_P:{self.real_port_priv}")
            return True
            
        except OSError as e:
            print(f"[X] Error iniciando servidores: {e}")
            return False

    def enviar_udp_broadcast(self, data_bytes):
        """Envía datagrama a 255.255.255.255"""
        try:
            # Enviar a broadcast
            # Reduce Noise: Don't log PING broadcasts
            if b'"filter": "PING"' not in data_bytes:
                print(f"[OUT_UDP_BC] {data_bytes.strip()}", file=sys.stderr)
            
            self.sock_udp.sendto(data_bytes, ('<broadcast>', PORT_DISCOVERY))
        except OSError as e:
            print(f"[!] Error UDP Broadcast: {e}")

    def enviar_udp_unicast(self, ip_destino, data_bytes):
        """Envía datagrama a una IP específica"""
        try:
            self.sock_udp.sendto(data_bytes, (ip_destino, PORT_DISCOVERY))
        except OSError as e:
            print(f"[!] Error UDP Unicast: {e}")

    def conectar_tcp(self, host, puerto):
        """
        Inicia conexión TCP saliente (LAN directa o WAN vía Tor SOCKS5).
        Retorna el socket conectado si éxito, o None.
        """
        try:
            if str(host).endswith(".onion"):
                s = self._conectar_socks5(host, puerto, timeout=40.0)
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0) # Timeout corto para LAN
                s.connect((host, puerto))

            s.setblocking(False)
            self.inputs.append(s)
            self.tcp_connections.append(s)
            return s
        except OSError as e:
            print(f"[!] Error conectar_tcp a {host}:{puerto} -> {e}", file=sys.stderr)
            return None

    def cerrar_tcp(self, sock):
        """Cierra un socket de forma segura y limpia listas"""
        if sock in self.inputs:
            self.inputs.remove(sock)
        if sock in self.tcp_connections:
            self.tcp_connections.remove(sock)
        try:
            sock.close()
        except OSError:
            pass

    def enviar_tcp(self, sock, data_bytes):
        """Envía datos por un socket TCP existente"""
        try:
            try:
                peer = sock.getpeername()
            except:
                peer = "Unknown"
            
            log_data = data_bytes.strip()
            if len(log_data) > 2000:
                log_data = f"(Large) {len(log_data)} bytes"
                
            print(f"[OUT_TCP] -> {peer}: {log_data}", file=sys.stderr)
            
            try:
                sock.setblocking(True)
                sock.sendall(data_bytes + b'\n')
                sock.setblocking(False)
                return True
            except Exception as e:
                print(f"[X] Sendall failed to {peer}: {e}", file=sys.stderr)
                sock.setblocking(False)
                raise e
        except Exception as e:
            print(f"[X] Error critico enviar_tcp: {e}", file=sys.stderr)
            self.cerrar_tcp(sock)
            return False

    def get_sockets_lectura(self):
        """Retorna la lista actual de sockets para select()"""
        return self.inputs

    def aceptar_conexion(self, server_sock):
        """Acepta un nuevo cliente TCP y lo añade al pool"""
        try:
            client, addr = server_sock.accept()
            client.setblocking(False)
            self.inputs.append(client)
            self.tcp_connections.append(client)
            return client, addr
        except OSError:
            return None, None

    def _pool_get(self, host, port):
        """
        Devuelve un socket vivo del pool para (host, port), o None si no hay / está muerto.
        Remueve sockets muertos automáticamente.
        """
        key = (host, port)
        with self._pool_lock:
            s = self._onion_pool.get(key)
        if s is None:
            return None
        # Verificar que el socket sigue vivo
        try:
            if s.fileno() < 0:
                raise OSError("fileno<0")
            # select no bloqueante: si hay error, está muerto
            r, _, e = select.select([s], [], [s], 0)
            if e:
                raise OSError("socket error flag")
            if r:
                # Hay datos pendientes: podría ser EOF del otro lado
                peek = s.recv(1, socket.MSG_PEEK)
                if not peek:
                    raise OSError("EOF detectado")
        except Exception as dead_err:
            print(f"[POOL] Socket muerto para {host}:{port} ({dead_err}), removiendo.", file=sys.stderr)
            with self._pool_lock:
                self._onion_pool.pop(key, None)
            try: s.close()
            except: pass
            return None
        return s

    def _pool_set(self, host, port, sock):
        """Registra un socket en el pool de forma thread-safe."""
        with self._pool_lock:
            # Si había uno viejo, cerrarlo
            old = self._onion_pool.get((host, port))
            if old and old is not sock:
                try: old.close()
                except: pass
            self._onion_pool[(host, port)] = sock

    def pool_close(self, host, port):
        """Cierra y elimina la conexión poolada para (host, port). Llamar al cerrar un chat."""
        key = (host, port)
        with self._pool_lock:
            s = self._onion_pool.pop(key, None)
        if s:
            try: s.close()
            except: pass
            print(f"[POOL] Conexión cerrada y removida: {host}:{port}", file=sys.stderr)

    def pool_close_all(self):
        """Cierra todas las conexiones del pool (al apagar el motor)."""
        with self._pool_lock:
            items = list(self._onion_pool.items())
            self._onion_pool.clear()
        for (h, p), s in items:
            try: s.close()
            except: pass

    def enviar_tcp_priv(self, ip_o_host, data_bytes, port=PORT_PRIVATE):
        """
        Envía un mensaje TCP al puerto Privado (LAN o WAN Tor).
        Para destinos .onion usa un pool de conexiones persistentes para evitar
        el overhead de circuit setup en cada mensaje (principal causa de latencia alta).
        Patrón LAN: Connect -> Send -> Close (LAN es rápido, sin overhead).
        Patrón Tor: Pool -> Send (reutiliza circuito existente; solo el primer msg paga el costo).
        """
        try:
            is_onion = str(ip_o_host).endswith(".onion")
            
            if is_onion:
                # --- Intentar reutilizar conexión del pool ---
                s = self._pool_get(ip_o_host, port)
                
                if s:
                    # Tenemos conexión viva: enviar directamente
                    try:
                        s.sendall(data_bytes + b'\n')
                        if len(data_bytes) > 2000:
                            print(f"[OUT_TCP_POOL] -> {ip_o_host}:{port}: (Large) {len(data_bytes)}b", file=sys.stderr)
                        else:
                            print(f"[OUT_TCP_POOL] -> {ip_o_host}:{port}: {data_bytes.strip()}", file=sys.stderr)
                        return True
                    except Exception as send_err:
                        # Conexión rota en envío: limpiar pool y reconectar
                        print(f"[POOL] Envío falló en socket poolado ({send_err}), reconectando...", file=sys.stderr)
                        self.pool_close(ip_o_host, port)
                        s = None
                
                # --- Sin conexión en pool (o recién limpiada): crear nueva ---
                print(f"[POOL] Creando nueva conexión Tor a {ip_o_host}:{port}...", file=sys.stderr)
                s = self._conectar_socks5(ip_o_host, port, timeout=60.0)
                # Mantener el socket en modo bloqueante para envíos síncronos
                s.settimeout(30.0)
                s.sendall(data_bytes + b'\n')
                # Registrar en pool para reusar en mensajes futuros
                self._pool_set(ip_o_host, port, s)
                
                if len(data_bytes) > 2000:
                    print(f"[OUT_TCP_PRIV_NEW] -> {ip_o_host}:{port}: (Large) {len(data_bytes)}b", file=sys.stderr)
                else:
                    print(f"[OUT_TCP_PRIV_NEW] -> {ip_o_host}:{port}: {data_bytes.strip()}", file=sys.stderr)
                return True

            else:
                # LAN: conexión transitoria (sin pool, LAN no tiene overhead)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(15.0)
                s.connect((ip_o_host, port))
                if len(data_bytes) > 2000:
                    print(f"[OUT_TCP_PRIV] -> {ip_o_host}:{port}: (Large) {len(data_bytes)}b", file=sys.stderr)
                else:
                    print(f"[OUT_TCP_PRIV] -> {ip_o_host}:{port}: {data_bytes.strip()}", file=sys.stderr)
                s.sendall(data_bytes + b'\n')
                s.close()
                return True

        except Exception as e:
            print(f"[X] Error TCP Priv a {ip_o_host}:{port}: {e}", file=sys.stderr)
            return False

    def registrar_socket_tcp(self, sock, label=None):
        """Registra un socket creado externamente en el pool de monitoreo"""
        if sock not in self.inputs:
            self.inputs.append(sock)
        if sock not in self.tcp_connections:
            self.tcp_connections.append(sock)
        # Nota: label no se usa en select, es para debug si quisiéramos loggear
