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
        
        self.tcp_connections = []  # Lista de sockets TCP activos (conectados o aceptados)
        self.inputs = []           # Lista para select()

    def iniciar_servidores(self):
        """Levanta los 3 sockets principales en modo escucha"""
        try:
            # 1. UDP Discovery
            self.sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_udp.bind(('0.0.0.0', PORT_DISCOVERY))
            self.sock_udp.setblocking(False)
            
            # 2. TCP Groups
            self.sock_tcp_group = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_tcp_group.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_tcp_group.bind(('0.0.0.0', PORT_GROUP))
            self.sock_tcp_group.listen(10)
            self.sock_tcp_group.setblocking(False)
            
            # 3. TCP Private
            self.sock_tcp_priv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_tcp_priv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock_tcp_priv.bind(('0.0.0.0', PORT_PRIVATE))
            self.sock_tcp_priv.listen(5)
            self.sock_tcp_priv.setblocking(False)
            
            # Preparar inputs para select
            self.inputs = [self.sock_udp, self.sock_tcp_group, self.sock_tcp_priv]
            
            print(f"[*] Transportes iniciados: UDP:{PORT_DISCOVERY}, TCP:{PORT_GROUP}, TCP:{PORT_PRIVATE}")
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

    def conectar_tcp(self, ip, puerto):
        """
        Inicia conexión TCP saliente.
        Retorna el socket conectado si éxito, o None.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0) # Timeout corto para conectar
            s.connect((ip, puerto))
            s.setblocking(False)
            self.inputs.append(s)
            self.tcp_connections.append(s)
            return s
        except OSError:
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
            # Protocolo simple: Longitud (4 bytes) + Body
            # Para evitar fragmentación/pegado en el stream
            # *Nota*: Arquitectura v2.0 dice JSON puro, pero TCP requiere framing.
            # Asumiremos que el receptor lee JSON válidos, pero lo ideal es enviar longitud.
            # Si enviamos JSON crudo, el receptor depende de detectar llaves {} o buffers.
            # Implementaremos un simple delimitador de nueva línea por simplicidad
            # o longitud si queremos ser robustos.
            # "Se elimina el uso de separadores propietarios... Todo es JSON" -> 
            # y que el receptor lea readline().
            
            try:
                peer = sock.getpeername()
            except:
                peer = "Unknown"
            
            log_data = data_bytes.strip()
            if len(log_data) > 2000:
                log_data = f"(Large) {len(log_data)} bytes"
                
            print(f"[OUT_TCP] -> {peer}: {log_data}", file=sys.stderr)
            
            # Reliable Send: Block momentarily to ensure full delivery without complex buffering
            try:
                sock.setblocking(True)
                sock.sendall(data_bytes + b'\n')
                sock.setblocking(False)
                return True
            except Exception as e:
                print(f"[X] Sendall failed to {peer}: {e}", file=sys.stderr)
                sock.setblocking(False) # Restore just in case
                raise e # Re-raise to trigger generic handler or just return False
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

    def enviar_tcp_priv(self, ip, data_bytes):
        """
        Envía un mensaje TCP transitorio al puerto Privado (44494).
        Patrón: Connect -> Send -> Close. Ideal para Handshakes (REQ/ACK/NO)
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15.0) # More time for large files
            s.connect((ip, PORT_PRIVATE))
            
            if len(data_bytes) > 2000:
                print(f"[OUT_TCP_PRIV] -> {ip}: (Large Payload) {len(data_bytes)} bytes", file=sys.stderr)
            else:
                print(f"[OUT_TCP_PRIV] -> {ip}: {data_bytes.strip()}", file=sys.stderr)
            
            s.sendall(data_bytes + b'\n')
            s.close()
            return True
        except Exception as e:
            print(f"[X] Error TCP Priv Transient a {ip}: {e}", file=sys.stderr)
            return False

    def registrar_socket_tcp(self, sock, label=None):
        """Registra un socket creado externamente en el pool de monitoreo"""
        if sock not in self.inputs:
            self.inputs.append(sock)
        if sock not in self.tcp_connections:
            self.tcp_connections.append(sock)
        # Nota: label no se usa en select, es para debug si quisiéramos loggear
