import socket
import threading
import sys
import time
import errno

# --- PROTOCOL v2.0 CONSTANTS ---
PKT_START_CMD = "[CMD]"
PKT_END_CMD   = "[CMD]"

PKT_START_MSJ = "[MSJ]"
PKT_END_MSJ   = "[MSJ]"

PKT_START_MPP = "[MPP]"
PKT_END_MPP   = "[MPP]"

PKT_START_LS  = "[LS]"
PKT_END_LS    = "[LS]"

SEP = "|"
SUB_SEP = ";"

# --- PORT MAP v2.0 ---
TCP_PORT_PRIV = 44494  # Chat Privado (1 a 1)
UDP_PORT_DISC = 44495  # Control y Descubrimiento (Broadcast)
TCP_PORT_GRP  = 44496  # Chat Grupal (Mesh)

# Backward Compatibility Aliases (Deprecated)
TCP_PORT = TCP_PORT_PRIV
UDP_PORT = UDP_PORT_DISC

PKT_PREFIX = PKT_START_CMD
TAG_MARK = "|TAG|" # Dummy
LEN_MARK = "|LEN|" # Dummy

def build_packet(cmd_name, *args):
    """Wrapper Legacy -> V2 CMD"""
    return build_cmd(cmd_name, *args)

BUFFER_SIZE = 8192

# --- BUILDERS (PACKET CONSTRUCTION) ---

def build_mpp(ip, nick, status, version):
    """
    Construye un Personal Package [MPP].
    [MPP]4|IP|Nick|Estado|Version[MPP] (Now using SUB_SEP inside)
    """
    # Sanitize inputs to prevent injection
    nick_safe = str(nick).replace(SEP, "").replace(SUB_SEP, "")
    stat_safe = str(status).replace(SEP, "").replace(SUB_SEP, "")
    ver_safe  = str(version).replace(SEP, "").replace(SUB_SEP, "")
    
    args = [ip, nick_safe, stat_safe, ver_safe]
    payload = SUB_SEP.join(args)
    return f"{PKT_START_MPP}{len(args)}{SUB_SEP}{payload}{PKT_END_MPP}"

def build_ls(mpp_list):
    """
    Construye un List Package [LS] a partir de una lista de strings [MPP].
    [LS]N|[MPP]...|[MPP]...[LS]
    """
    count = len(mpp_list)
    payload = SEP.join(mpp_list) if count > 0 else ""
    return f"{PKT_START_LS}{count}{SEP}{payload}{PKT_END_LS}"

def build_cmd(cmd_name, *args):
    """
    Construye un Comando [CMD].
    Structure: [CMD]NAME|N|Arg1|Arg2...[CMD]
    """
    valid_args = [str(a) for a in args]
    payload = SEP.join(valid_args) if valid_args else ""
    
    mid = f"{cmd_name}{SEP}{len(valid_args)}"
    if valid_args:
        mid += SEP + payload
        
    return f"{PKT_START_CMD}{mid}{PKT_END_CMD}".encode('utf-8')

def build_msj(mpp_str, type_str, specific_args_list, msg_content):
    """
    Construye un MSJ.
    [MSJ]TotalArgs|MPP|TYPE|...|LEN|BODY[MSJ]
    """
    # Args: MPP + TYPE + Specifics + [Msg]
    # Length passed as separate field prior to Body?
    # Protocol: 
    # Arg0: MPP
    # Arg1: Type
    # Arg2..N: Specifics
    # ArgLast-1: LEN(BODY)
    # ArgLast: BODY
    
    # Let's count args.
    # MPP is 1 arg. Type is 1 arg. Specifics is N args.
    # LEN is 1 arg. Body is 1 arg.
    
    s_args = [str(a) for a in specific_args_list]
    
    pre_payload_parts = [mpp_str, type_str] + s_args + [str(len(msg_content))]
    pre_payload = SEP.join(pre_payload_parts)
    
    # Total args count = len(pre_payload_parts) + 1 (Body)
    count = len(pre_payload_parts) + 1
    
    # Encoding Body logic
    if isinstance(msg_content, str): msg_bytes = msg_content.encode('utf-8')
    else: msg_bytes = msg_content
    
    # Final Payload = PrePayload + SEP + Body
    # We construct string header first
    header_str = f"{PKT_START_MSJ}{count}{SEP}{pre_payload}{SEP}"
    
    # Return bytes concatenation
    return header_str.encode('utf-8') + msg_bytes + PKT_END_MSJ.encode('utf-8')

# --- PARSERS ---

def parse_packet(raw_data):
    """
    Analiza bytes o string y retorna estructura.
    Retorna tupla: (Tipo, Nombre/Subtipo, ArgsList)
    ArgsList para MSJ incluye el cuerpo como último elemento.
    """
    try:
        # Handle bytes vs str
        if isinstance(raw_data, bytes):
            try:
                raw_str = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                return ('ERR', None, [])
        else:
            raw_str = raw_data
            
        raw_str = raw_str.strip()
        
        # 1. COMMANDS
        if raw_str.startswith(PKT_START_CMD) and raw_str.endswith(PKT_END_CMD):
            content = raw_str[len(PKT_START_CMD):-len(PKT_END_CMD)]
            parts = content.split(SEP)
            if len(parts) < 2: return ('ERR', None, [])
            
            cmd_name = parts[0]
            try: n_args = int(parts[1])
            except: return ('ERR', None, [])
            
            args = parts[2:]
            return ('CMD', cmd_name, args)

        # 2. MESSAGES
        elif raw_str.startswith(PKT_START_MSJ): # Ends check tricky if body has newlines? No strip() removed it?
            # Re-check endswith using the original raw_str (strip might hurt body?)
            if not raw_str.endswith(PKT_END_MSJ):
                 return ('ERR', None, [])
                 
            content = raw_str[len(PKT_START_MSJ):-len(PKT_END_MSJ)]
            
            # Logic: First field is Total Args
            # Format: COUNT|MPP|TYPE|...|LEN|BODY
            
            first_sep = content.find(SEP)
            if first_sep == -1: return ('ERR', None, [])
            
            try: count = int(content[:first_sep])
            except: return ('ERR', None, [])
            
            remainder = content[first_sep+1:]
            
            # Split into exactly 'count' parts
            # But the last part (BODY) might contain SEP.
            # So we split count-1 times from left, and the rest is Body.
            
            payload_parts = remainder.split(SEP, count - 1)
            
            # Extract MPP and Type to conform standard return
            if len(payload_parts) < 2: return ('ERR', None, [])
            
            # Return ('MSJ', TYPE, ArgsList)
            # ArgsList = [MPP, TYPE, ..., BODY]
            type_str = payload_parts[1]
            return ('MSJ', type_str, payload_parts)
            
        return ('RAW', None, [raw_str])
        
    except:
        return ('ERR', None, [])

def extract_mpp(mpp_str):
    """
    Parsea un bloque [MPP] y devuelve dict.
    """
    if not mpp_str or not mpp_str.startswith(PKT_START_MPP) or not mpp_str.endswith(PKT_END_MPP):
        return None
    content = mpp_str[len(PKT_START_MPP):-len(PKT_END_MPP)]
    parts = content.split(SUB_SEP)
    # Format: N|IP|Nick|Stat|Ver
    if len(parts) < 5: return None
    return {'ip': parts[1], 'nick': parts[2], 'status': parts[3], 'ver': parts[4]}

# --- NETWORK SENDING ---

def send_tcp_packet(ip, data, port=TCP_PORT_PRIV):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ip, port))
        s.sendall(data)
        s.close()
    except Exception: pass

def send_udp_broadcast(data, port=UDP_PORT_DISC):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(data, ('<broadcast>', port))
    except: pass

def send_udp_unicast(ip, data, port=UDP_PORT_DISC):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(data, (ip, port))
    except: pass

def send_cmd(ip, cmd_name, *args):
    """
    Wrapper inteligente v2.0
    Decide protocolo y puerto según comando.
    """
    pkt = build_cmd(cmd_name, *args)
    
    # UDP COMMANDS (Discovery)
    udp_cmds = ["SEARCH_GROUP", "I_EXIST", "WHOIS", "IAM_HERE", "DISCONNECT_ALL"]
    
    if cmd_name in udp_cmds:
        if cmd_name == "SEARCH_GROUP" or cmd_name == "DISCONNECT_ALL":
             send_udp_broadcast(pkt)
        else:
             send_udp_unicast(ip, pkt)
    else:
        # TCP Routing
        target_port = TCP_PORT_PRIV
        if cmd_name in ["JOIN_GROUP", "WELCOME_GROUP", "LEAVE_GROUP", "I_ANSWER", "GRP_MSG"]:
             target_port = TCP_PORT_GRP # 44496 Mesh Port
             
        send_tcp_packet(ip, pkt, target_port)

def send_cmd_all(cmd_name, *args):
    # Forced Broadcast
    pkt = build_cmd(cmd_name, *args)
    send_udp_broadcast(pkt)

# --- LISTENERS ---

def start_tcp_listener(port, callback_func):
    """Generic TCP Listener"""
    def _loop():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(('0.0.0.0', port))
            s.listen(10)
        except: return

        while True:
            try:
                conn, addr = s.accept()
                # Read specific buffer size
                raw = conn.recv(BUFFER_SIZE).decode('utf-8', errors='ignore')
                if raw:
                    callback_func(conn, addr[0], raw)
                conn.close()
            except: pass
            
    threading.Thread(target=_loop, daemon=True).start()

def start_udp_listener(port, callback_func):
    """Generic UDP Listener"""
    def _loop():
        u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        u.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try: u.bind(('', port))
        except: return

        while True:
            try:
                data, addr = u.recvfrom(BUFFER_SIZE)
                callback_func(data, addr[0])
            except: pass
            
    threading.Thread(target=_loop, daemon=True).start()
