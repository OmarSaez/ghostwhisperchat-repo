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

class GestorRed:
    def __init__(self):
        self.sock_udp = None       # 44495
        self.sock_tcp_group = None # 44496 (Listen)
        self.sock_tcp_priv = None  # 44494 (Listen)
        
        self.socks_host = "127.0.0.1"
        self.socks_port = 9050
        
        self.tcp_connections = []  # Lista de sockets TCP activos (conectados o aceptados)
        self.inputs = []           # Lista para select()

    def set_socks_proxy(self, host="127.0.0.1", port=9050):
        """Configura los parámetros del proxy SOCKS5 local para Tor"""
        self.socks_host = host
        self.socks_port = port

    def _conectar_socks5(self, host, port, timeout=15.0):
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
                s = self._conectar_socks5(host, puerto, timeout=15.0)
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

    def enviar_tcp_priv(self, ip_o_host, data_bytes, port=PORT_PRIVATE):
        """
        Envía un mensaje TCP transitorio al puerto Privado (LAN o WAN Tor).
        Patrón: Connect -> Send -> Close. Ideal para Handshakes (REQ/ACK/NO)
        """
        try:
            is_onion = str(ip_o_host).endswith(".onion")
            if is_onion:
                s = self._conectar_socks5(ip_o_host, port, timeout=15.0)
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(15.0) # More time for large files
                s.connect((ip_o_host, port))
            
            if len(data_bytes) > 2000:
                print(f"[OUT_TCP_PRIV] -> {ip_o_host}:{port}: (Large Payload) {len(data_bytes)} bytes", file=sys.stderr)
            else:
                print(f"[OUT_TCP_PRIV] -> {ip_o_host}:{port}: {data_bytes.strip()}", file=sys.stderr)
            
            s.sendall(data_bytes + b'\n')
            s.close()
            return True
        except Exception as e:
            print(f"[X] Error TCP Priv Transient a {ip_o_host}:{port}: {e}", file=sys.stderr)
            return False

    def registrar_socket_tcp(self, sock, label=None):
        """Registra un socket creado externamente en el pool de monitoreo"""
        if sock not in self.inputs:
            self.inputs.append(sock)
        if sock not in self.tcp_connections:
            self.tcp_connections.append(sock)
        # Nota: label no se usa en select, es para debug si quisiéramos loggear
