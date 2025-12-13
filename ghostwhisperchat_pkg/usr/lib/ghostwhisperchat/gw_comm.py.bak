import socket
import threading
import sys
import time

# --- CONSTANTS (Recovered from Backup v33.12) ---
PKT_PREFIX = "[CMD]"
SEP = "<SEPARATOR>"  # Changed back from "|" to avoid delimiter collision
TAG_MARK = "<TAG>"
LEN_MARK = "<LEN>"

UDP_PORT = 44495
TCP_PORT = 44494

def build_packet(cmd_name, *args):
    """
    Construye paquete: [CMD]<TAG>NOMBRE<TAG><LEN>N<LEN><SEP>ARG1<SEP>ARG2...
    """
    valid_args = [str(a) for a in args]
    # Header format compatible with v33.12
    # NOTE: Backup included a trailing SEP after header. We replicate that for max compatibility.
    # Logic: "Header...<SEP>" + "PayloadJoined"
    
    header = f"{PKT_PREFIX}{TAG_MARK}{cmd_name}{TAG_MARK}{LEN_MARK}{len(valid_args)}{LEN_MARK}"
    
    # We explicitly join with SEP. 
    # If we want to strictly match backup "header...<SEP>payload":
    # header += SEP
    # payload = SEP.join(valid_args)
    # return (header + payload).encode()
    
    # Let's use the explicit robust construction:
    payload = SEP.join(valid_args)
    
    # To ensure 100% match with Backup parser logic:
    # Backup parser expects lparts[2] to start with SEP (payload starts with SEP).
    # So we MUST add the SEP acting as boundary.
    full_pkt_str = f"{header}{SEP}{payload}"
    return full_pkt_str.encode('utf-8')

def parse_packet(raw_str):
    """
    Parsea un string crudo. 
    Retorna: (EsComando, NombreCmd, ListaArgs)
    """
    if not raw_str.startswith(PKT_PREFIX):
        return (False, None, None)
    
    try:
        parts = raw_str.split(TAG_MARK) 
        if len(parts) < 3: return (False, None, None)
        cmd_name = parts[1]
        
        rest = parts[2]
        lparts = rest.split(LEN_MARK)
        if len(lparts) < 3: return (False, None, None)
        n_args = int(lparts[1])
        
        # lparts[2] should be "<SEP>ARG1<SEP>ARG2..."
        args_payload = lparts[2]
        
        # Check boundary
        if args_payload.startswith(SEP):
            args_payload = args_payload[len(SEP):]
            
        if n_args == 0:
            args = []
        else:
            args = args_payload.split(SEP)
            
        return (True, cmd_name, args)
        
    except Exception as e:
        return (False, None, None)

# --- SENDING UTILS ---

def send_tcp_packet(ip, data):
    """Envia datos raw via TCP (Reliable)"""
    try:
        if isinstance(data, str): data = data.encode('utf-8')
        
        # print(f"[GW_COMM] TCP -> {ip}") 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ip, TCP_PORT))
        s.sendall(data)
        s.close()
    except Exception as e:
        # print(f"[GW_COMM] TCP Error to {ip}: {e}")
        pass

def send_udp_cmd(ip, cmd, *args):
    """Envía un comando UDP simple (Fire & Forget)"""
    try:
        data = build_packet(cmd, *args)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(data, (ip, UDP_PORT))
    except: pass

def send_udp_cmd_all(cmd, *args):
    """Envía un comando UDP a la dirección de broadcast"""
    try:
        data = build_packet(cmd, *args)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(data, ('255.255.255.255', UDP_PORT))
    except: pass

def send_cmd(ip, cmd, *args):
    """
    Wrapper inteligente: Elige TCP o UDP según el tipo de comando.
    """
    # Commands that MUST use UDP (Discovery)
    udp_cmds = ["WHO_ALL", "IAM_HERE", "WHOIS", "USER_HERE", "SEARCH_GROUP", "I_EXIST"]
    
    if cmd in udp_cmds:
        send_udp_cmd(ip, cmd, *args)
    else:
        # Default TCP (Handshakes, Invites, etc)
        pkt = build_packet(cmd, *args)
        send_tcp_packet(ip, pkt)

def send_cmd_all(cmd, *args):
    # Broadcast is always UDP
    send_udp_cmd_all(cmd, *args)

# --- LISTENER LOGIC (Modularized) ---

def start_tcp_listener(callback_func):
    """
    Starts the TCP listener thread.
    callback_func(socket_obj, ip_addr, raw_data_str) -> bool
    Return True to keep socket open (threaded handoff), False to close it.
    """
    def _loop():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('0.0.0.0', TCP_PORT))
            s.listen(10)
        except Exception as e:
            print(f"Error binding TCP {TCP_PORT}: {e}")
            return # Critical failure

        while True:
            try:
                conn, addr = s.accept()
                ip = addr[0]
                
                # Peek or read first chunk? Logic requires reading to know if it's cmd.
                # Standard logic: read 4096.
                try:
                    raw = conn.recv(4096).decode('utf-8', errors='ignore')
                    if raw:
                        keep_open = callback_func(conn, ip, raw)
                        if not keep_open:
                            conn.close()
                    else:
                        conn.close()
                except:
                    conn.close()
            except Exception as e:
                pass # Accept error

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t

def start_udp_listener(callback_func):
    """
    Starts UDP listener thread.
    callback_func(raw_data_bytes, ip_addr)
    """
    def _loop():
        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            u.bind(('', UDP_PORT))
        except:
            return

        while True:
            try:
                data, addr = u.recvfrom(4096)
                if not data: continue
                callback_func(data, addr[0])
            except: pass
            
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t
