import socket
import sys
import os
import time

# --- CONSTANTS v27.0 ---
PKT_PREFIX = "[CMD]"
SEP = "|"
TAG_MARK = "<TAG>"
LEN_MARK = "<LEN>"
UDP_PORT = 44495
TCP_PORT = 44494 # v37.8 Added TCP Port


def build_packet(cmd_name, *args):
    """
    Construye paquete: [CMD]<TAG>NOMBRE<TAG><LEN>N<LEN><SEP>ARG1<SEP>ARG2...
    """
    payload = SEP.join(map(str, args))
    n_args = len(args)
    # Header: [CMD]<TAG>NAME<TAG><LEN>N<LEN>
    pkt = f"{PKT_PREFIX}{TAG_MARK}{cmd_name}{TAG_MARK}{LEN_MARK}{n_args}{LEN_MARK}"
    # Append payload with leading SEP? 
    # Logic in parse: if args_payload.startswith(SEP).
    # So we should prepend SEP to payload if N > 0 to be safe/consistent, 
    # OR the payload IS the SEP joined string.
    # Logic in parse: lparts[2] is payload.
    # If I join "a","b" -> "a|b".
    # payload is "a|b".
    # If I append it: ...<LEN>|a|b
    # parse: lparts[2] = "|a|b". startswith SEP? Yes. remove SEP -> "a|b". split -> ["a", "b"]. Correct.
    # So I must prepend SEP to the payload join.
    if n_args > 0:
        pkt += f"{SEP}{payload}"
    return pkt.encode('utf-8')

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
        
        args_payload = lparts[2]
        if args_payload.startswith(SEP):
            args_payload = args_payload[len(SEP):]
            
        if n_args == 0:
            args = []
        else:
            args = args_payload.split(SEP)
            
        return (True, cmd_name, args)
        
    except Exception as e:
        # print(f"ParsePacket Error: {e}") # Silent or handled by caller
        return (False, None, None)

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

# v37.8: TCP Logic moved here
TCP_PORT = 44494

def send_tcp_packet(ip, data):
    """Envia datos raw via TCP (Reliable)"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2); s.connect((ip, TCP_PORT))
        if isinstance(data, str): s.send(data.encode())
        else: s.send(data)
        s.close()
    except Exception as e:
        print(f"[GW_COMM] TCP Error to {ip}: {e}")
        # traceback.print_exc() if imported
        pass

def send_cmd(ip, cmd, *args):
    """
    Wrapper inteligente: Elige TCP o UDP según el tipo de comando.
    """
    udp_cmds = ["WHO_ALL", "IAM_HERE", "WHOIS", "USER_HERE", "SEARCH_GROUP", "I_EXIST"]
    
    if cmd in udp_cmds:
        send_udp_cmd(ip, cmd, *args)
    else:
        # Por defecto TCP (INVITE, INVITE_ACC, INVITE_REJ, etc)
        pkt = build_packet(cmd, *args)
        send_tcp_packet(ip, pkt)

def send_cmd_all(cmd, *args):
    """Broadcast UDP a todos"""
    send_udp_cmd_all(cmd, *args)
