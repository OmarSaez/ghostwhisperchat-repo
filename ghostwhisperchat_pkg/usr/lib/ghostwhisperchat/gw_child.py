
import os
import sys
import socket
import time
import shutil
import hashlib
import platform
import subprocess
import signal
import threading

import gw_comm
from gw_comm import PKT_PREFIX, SEP, TAG_MARK, LEN_MARK, UDP_PORT, TCP_PORT, build_packet
from gw_shared import Colors, COMMAND_DEFS, resolve_cmd, IPC_PORT, get_ip, calculate_file_hash

# --- LOCAL STATE & GLOBALS (Scoped to this process) ---
MY_NICK = "?"
MY_STATUS = "?"
MY_IP = get_ip()
CURRENT_CHAT_ID = None
IS_CHILD = True
MY_CHILD_ID = None
PROMPT = f"\001{Colors.B}\002Tú: \001{Colors.E}\002"
REMOTE_NICK = "?"
PEERS = {} # Local peers store for child context {ip: {nick, chats}}

BUFFER = 4096

def set_terminal_title(title):
    """Establece el título de la ventana de la terminal."""
    if platform.system() == "Windows":
        os.system(f"title {title}")
    else:
        sys.stdout.write(f"\x1b]2;{title}\x07")
        sys.stdout.flush()

def send_ipc(msg, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(msg.encode(), ('127.0.0.1', int(port)))
        s.close()
    except: pass

def send_file(arg):
    path = os.path.expanduser(arg.strip().strip("'\""))
    if not os.path.exists(path): return print(f"{Colors.F}[X] No existe.{Colors.E}") # isfile -> exists (for dirs)
    
    # Folder Support
    is_dir = os.path.isdir(path)
    to_send_path = path
    file_type = 'FILE'
    
    if is_dir:
        print(f"{Colors.W}[*] Comprimiendo carpeta '{os.path.basename(path)}'...{Colors.E}")
        tmp_zip_base = f".gwc_tmp_{int(time.time())}"
        shutil.make_archive(tmp_zip_base, 'zip', path)
        to_send_path = tmp_zip_base + ".zip"
        file_type = 'DIR'
    
    f_hash = calculate_file_hash(to_send_path)
    n, s = os.path.basename(to_send_path) if not is_dir else os.path.basename(path) + ".zip", os.path.getsize(to_send_path)

    # In Child context, we send to the remote peer of THIS chat.
    # We rely on PEERS logic or just send to the remote associated with this child.
    # But wait, run_child has `remote` arg.
    # We should use PEERS list if we are in a group, or just the one remote if Priv.
    pass
    # Implementation deferred to main loop access or we pass the target logic.
    # Actually, simpler: we need `remote` var from `run_child`.
    # Let's encapsulate send_file inside run_child or pass targets.
    # For now, I will inline the logic or use a helper that takes targets.
    return n, s, f_hash, file_type, to_send_path, is_dir

def show_help():
    lines = []
    lines.append(f" {Colors.BO}--- AYUDA Y COMANDOS (Versión Hija) ---{Colors.E}")
    # Simplified help for Child
    lines.append(" --archivo PATH : Enviar archivo")
    lines.append(" --exit         : Salir")
    lines.append(" --clear        : Limpiar pantalla")
    lines.append(" (Los comandos globales se reenvían al Lobby)")
    print("\n".join(lines))

def handle_child_sigint(cid, port):
    # Enviar señal de salida al lobby y morir
    try:
        send_ipc(f"CHILD_EXIT{SEP}{cid}", port)
    except: pass
    print(f"{Colors.W}[*] Cerrando chat...{Colors.E}")
    time.sleep(0.2)
    os._exit(0)

def join_grp(gid, gp, remote_ip, my_nick, my_status, update_peers_func):
    """
    Logic to search/join group UDP in Child.
    """
    # print(f"{Colors.G}[*] Conectando a '{gid}'...{Colors.E}")
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Note: gw_comm.build_packet is available
    pkt = build_packet("SEARCH_GROUP", gid, gp, my_nick, my_status)
    u.sendto(pkt, ('255.255.255.255', UDP_PORT)); u.close()
    
    # We rely on Lobby to actually 'connect' the peers? No, Lobby listeners handle incoming.
    # But Child doesn't have listeners.
    # Wait, the architecture is: Lobby handles ALL incoming (TCP/UDP) and forwards to Child via IPC.
    # So Child just sends the SEARCH packet. The responses (I_EXIST) go to Lobby UDP listener.
    # Lobby UDP listener updates PEERS and forwards FWD_PEER to child.
    # Child receives FWD_PEER via ipc_listen_child and updates local PEERS.
    pass

def ipc_listen_child(my_port, lock_state):
    global MY_CHILD_ID, PEERS
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: u.bind(('127.0.0.1', int(my_port)))
    except Exception as e: 
        print(f"Error bind child IPC: {e}")
        return
    
    while True:
        try:
            d, _ = u.recvfrom(8192); msg = d.decode()
            p = msg.split(SEP)
            cmd = p[0]
            
            if cmd == "FWD_MSG":
                if len(p) >= 4:
                    cid, tag, text = p[1], p[2], p[3]
                    if cid == MY_CHILD_ID:
                        # Clean print
                        print(f"{tag}: {text}") 
                        
                        # Logic Smart Popup (Update state)
                        lock_state['last_rx'] = time.time()
                        # Handling Popups is done in Lobby usually?
                        # No, IPC listener in Lobby is one thing.
                        # This is CHILD listener.
                        # Wait, the popup logic I saw earlier was in `ghostwhisperchat::ipc_listen_child`.
                        # It sends Popups from the Child process?
                        # Yes, `popup` function was in `ghostwhisperchat`.
                        # But `popup` uses `zenity` etc.
                        # If we move this to `gw_child.py`, we need `popup` function here too?
                        # Or we remove popup logic from child and let Lobby handle it?
                        # The code `ghostwhisperchat` had `ipc_listen_child` executing `popup`.
                        # So each child is responsible for its own popups?
                        # That implies `popup` function must be available here.
                        pass

            elif cmd == "FWD_FILE":
                if len(p) >= 4 and p[1] == MY_CHILD_ID:
                    print(f"{Colors.W}[⇩] Archivo '{p[3]}' de {p[2]} recibido en Lobby.{Colors.E}")
            
            elif cmd == "FWD_PEER":
                if len(p) >= 4:
                    rmt_ip, rmt_nick, rmt_stat = p[1], p[2], p[3]
                    if rmt_ip not in PEERS: PEERS[rmt_ip] = {'nick': rmt_nick, 'chats': {MY_CHILD_ID}}
                    else: 
                         if isinstance(PEERS[rmt_ip], dict):
                             PEERS[rmt_ip]['nick'] = rmt_nick
                             PEERS[rmt_ip]['chats'].add(MY_CHILD_ID)
                    print(f"{Colors.G}[+] Detectado: {rmt_nick}{Colors.E}")
            
            elif cmd == "CMD_CLOSE_NOW":
                print(f"\n{Colors.F}[💔] {lock_state.get('remote_nick','?')} ha abandonado el chat.{Colors.E}")
                time.sleep(3)
                os._exit(0)

        except: pass

def run(cid, ctype, remote, password, mynick, mystatus, myport, rnick="?"):
    global MY_NICK, MY_STATUS, MY_IP, CURRENT_CHAT_ID, IS_CHILD, MY_CHILD_ID, PROMPT, REMOTE_NICK, PEERS
    IS_CHILD = True
    MY_CHILD_ID = cid
    CURRENT_CHAT_ID = cid
    
    MY_NICK = mynick
    MY_STATUS = mystatus
    REMOTE_NICK = rnick 
    
    # Signals
    signal.signal(signal.SIGINT, lambda s, f: handle_child_sigint(cid, myport))
    
    # Shared State for Popups (Partial implementation - Popup logic is complex to port fully without `popup` func)
    # For now we skip the actual Popup execution in this modular version unless we port `popup`.
    # But we update the state for tracking.
    pop_state = {'last_input': 0, 'last_rx': time.time(), 'pop_off': False, 'type': ctype, 'remote_id': remote, 'remote_nick': rnick}

    # Header
    if ctype == 'GROUP':
        header_txt = f"== CHAT GRUPAL {remote} =="
        set_terminal_title(f"GRUP {remote}")
    else:
        header_txt = f"== CHAT PRIVADO CON {rnick} =="
        set_terminal_title(f"PRIV {rnick}")
        
    print(f"{Colors.H}{header_txt}{Colors.E}")
    
    # Start IPC
    threading.Thread(target=ipc_listen_child, args=(myport, pop_state), daemon=True).start()
    
    # Start Logic
    if ctype == 'GROUP':
        # join_grp just sends the SEARCH packet
        threading.Thread(target=join_grp, args=(remote, password, remote, MY_NICK, MY_STATUS, None), daemon=True).start()
    elif ctype == 'PRIV':
        if remote not in PEERS: 
             PEERS[remote] = {'nick': rnick, 'chats': {cid}}
        # Send WHOIS to trigger handshake/presence
        gw_comm.send_cmd(remote, "WHOIS", MY_IP) 

    while True:
        try:
            inp = input(PROMPT).strip()
            if not inp: continue
            
            pop_state['last_input'] = time.time()
            
            parts = inp.split(" ", 1)
            raw_cmd = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            cmd_key = resolve_cmd(raw_cmd)

            if cmd_key == 'EXIT':
                print(f"{Colors.W}[*] Saliendo...{Colors.E}")
                send_ipc(f"FWD_CMD{SEP}{cid}{SEP}--exit", myport) # Send to SELF/Lobby IPC port? 
                # Wait, Lobby listens on IPC_PORT (5000). Child listens on myport (5001+).
                # To tell Lobby "I want to exit", we must send to IPC_PORT (5000).
                # The helper `send_ipc` connects to the port passed.
                # Use shared IPC_PORT from gw_shared
                send_ipc(f"FWD_CMD{SEP}{cid}{SEP}--exit", IPC_PORT)
                time.sleep(0.5)
                os._exit(0)

            elif cmd_key == 'POP_OFF':
                pop_state['pop_off'] = True
                print(f"{Colors.W}[i] Popups DESACTIVADOS.{Colors.E}")
                continue
            elif cmd_key == 'POP_ON':
                pop_state['pop_off'] = False
                print(f"{Colors.G}[i] Popups ACTIVADOS.{Colors.E}")
                continue
            
            elif cmd_key == 'FILE':
                 if args: 
                     # Logic to send file
                     # 1. Prepare file
                     try:
                         n, s, f_hash, ftype, fpath, is_dir = send_file(args)
                     except:
                         continue
                     
                     # 2. Determine Targets
                     targets = []
                     if ctype == 'GROUP':
                         # In group, we might want to send to all peers we know in this chat?
                         # Or simpler: The underlying `send_tcp_packet` needs an IP.
                         # We iterate PEERS.
                         for ip, d in PEERS.items():
                             if cid in d.get('chats', set()):
                                 targets.append(ip)
                     else:
                         targets.append(remote)
                     
                     if not targets:
                         print(f"{Colors.F}[X] Nadie en el chat.{Colors.E}")
                         continue
                     
                     print(f"{Colors.W}[⇧] Enviando '{n}' ({s} bytes)...{Colors.E}")
                     cnt = 0
                     for ip in targets:
                         if ip == MY_IP: continue
                         try:
                             # Send Header
                             pkt = build_packet("FILE_TRANSFER", n, s, f_hash, ftype)
                             gw_comm.send_tcp_packet(ip, pkt) 
                             # Wait a bit?
                             time.sleep(0.1)
                             # Send Content (Stream)
                             # We need a new socket for content? 
                             # `gw_comm.send_tcp_packet` opens socket, sends, closes.
                             # If we follow that pattern, the Remote `handle_incoming_tcp` reads the packet.
                             # The Remote sees "FILE_TRANSFER" command.
                             # It spins up `dl_file` thread. `dl_file` expects to read from `sock`.
                             # BUT `send_tcp_packet` closes the socket immediately after sending header!
                             # This logic is BROKEN if we use standard `send_tcp_packet` for header then...
                             
                             # We need to manually open socket, send header, send body, close.
                             k = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                             k.settimeout(2)
                             k.connect((ip, TCP_PORT))
                             k.send(pkt)
                             time.sleep(0.1)
                             with open(fpath, "rb") as f:
                                 while True:
                                     d = f.read(BUFFER)
                                     if not d: break
                                     k.sendall(d)
                             k.close()
                             cnt += 1
                         except Exception as e:
                             print(f"Err Send {ip}: {e}")
                     
                     print(f"{Colors.G}[✔] Enviado a {cnt}.{Colors.E}")
                     if is_dir and os.path.exists(fpath): os.remove(fpath)

                 else: print(f"{Colors.F}Falta ruta.{Colors.E}")
                 continue
            
            elif cmd_key == 'CLEAR':
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"{Colors.H}--- CHAT {ctype} ({cid}) ---{Colors.E}")
                continue

            # Forward others to Lobby
            potential_cmd_key = resolve_cmd(raw_cmd)
            if potential_cmd_key or (raw_cmd == "--log" and len(inp.split())>1):
                 print(f"{Colors.W}[IPC] Enviando comando al Lobby...{Colors.E}")
                 send_ipc(f"FWD_CMD{SEP}{cid}{SEP}{inp}", IPC_PORT)
                 continue
            
            if cmd_key == 'HELP':
                show_help()
                continue
            
            # Send Chat Message
            if ctype == 'GROUP':
                 # Use gw_comm.send_cmd_all? No, GRP_MSG is sent to SPECIFIC GROUP ID via Multicast?
                 # No, version 37 uses `send_cmd_all` (Broadcast UDP) for GRP_MSG ??
                 # Check original code: `send_cmd_all("GRP_MSG", remote, inp)`
                 # Yes, it broadcasts to everyone "GRP_MSG <GID> <TEXT>". Everyone filters.
                 gw_comm.send_cmd_all("GRP_MSG", remote, inp)
            else:
                 # Private Message: TCP
                 # `send_all` in original was complex. It iterated peers.
                 # Here we just send to `remote` IP.
                 gw_comm.send_tcp_packet(remote, inp.encode())

        except KeyboardInterrupt:
             send_ipc(f"FWD_CMD{SEP}{cid}{SEP}--exit", IPC_PORT)
             try: sys.exit(0)
             except: os._exit(0)
        except Exception as e:
            print(f"{Colors.F}Error Child: {e}{Colors.E}")
