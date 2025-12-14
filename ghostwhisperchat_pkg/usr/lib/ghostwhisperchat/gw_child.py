
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
import gw_shared
from gw_shared import Colors, COMMAND_DEFS, resolve_cmd, IPC_PORT, get_ip, calculate_file_hash, APP_VERSION
import gw_cmd

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

class ChildAdapter:
    def __init__(self, cid, port, remote, ctype, rnick):
        self.cid = cid
        self.port = port
        self.remote = remote
        self.ctype = ctype
        self.remote_nick_init = rnick
        self.pop_off = False
        self.debug = False

    def reply(self, msg, cid):
        print(msg)

    def forward(self, cmd):
        # Forward to Lobby (IPC_PORT)
        send_ipc(f"FWD_CMD{SEP}{self.cid}{SEP}{cmd}", IPC_PORT)

    # --- Methods required by gw_cmd ---
    def create_group(self, id, pas): self.forward(f"--chatgrupal {id} {pas}")
    
    def find_global(self, args):
        # Simplistic local search for compatibility
        # Or forward? If we forward, context is lost.
        # find_global is used by CHAT_PRIV (create new chat).
        # Child should forward CHAT_PRIV creation.
        return None # Triggers forward or error in gw_cmd? 
        # Actually gw_cmd checks if t: ... else reply "Eres tu".
        # If I return None, gw_cmd does nothing?
        # NO, gw_cmd logic for CHAT_PRIV calls find_global.
        # If Child types --chatpersonal, it should probably be forwarded to Lobby which handles window spawning.
        # But gw_cmd will try to run local logic.
        # I should probably just forward CHAT_PRIV command entirely in process loop or here?
        pass

    def invite_priv(self, ip, nick, status): self.forward(f"--chatpersonal {ip}") # Helper

    def get_chat(self, cid):
        # Return dict mimicking ACTIVE_CHATS[cid]
        return {'type': self.ctype, 'remote_id': self.remote, 'remote_nick': REMOTE_NICK}

    def get_my_info(self): return MY_NICK, MY_IP, MY_STATUS
    def get_mpp(self): return gw_comm.build_mpp(MY_IP, MY_NICK, MY_STATUS, APP_VERSION)
    def get_peers(self): return PEERS
    def show_lobby_summary(self): pass # No logic for child
    
    def get_known_users(self):
         # Map PEERS to KNOWN_USERS format {ip: {nick, status, t}}
         ku = {}
         for ip, d in PEERS.items():
             ku[ip] = {'nick': d.get('nick','?'), 'status': '?', 't': time.time()}
         return ku

    def scan_network(self, cid): self.forward("--quienes")
    
    def set_config(self, key, val):
        # Some configs are local (pop_off), others global (nick, status)
        if key == 'nick': 
            self.forward(f"--nombre {val}")
        elif key == 'status': 
            self.forward(f"--estado {val}")
        elif key == 'pop_on':
            self.pop_off = not val
        # For others, forward config change?
        # gw_cmd calls set_config then save_config.
        # Child shouldn't overwrite config file directly usually (race condition).
        # Forwarding generic config update?
        pass

    def broadcast_status(self, st=None):
         # Child can broadcast status update to its peers?
         pass 

    def update_title(self):
        curr = f"GRUP {self.remote}" if self.ctype == 'GROUP' else f"PRIV {REMOTE_NICK}"
        set_terminal_title(curr)

    def toggle_autostart(self, val, cid): self.forward(f"--autolevantado-{'si' if val else 'no'}")
    
    def clear_screen(self, cid):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Colors.H}--- CHAT {self.ctype} ({self.cid}) ---{Colors.E}")

    def invite_users(self, args_str, cid):
        # Forward invite to Lobby to handle scanning/inviting properly
        self.forward(f"--invite {args_str}")

    def send_file(self, args, cid):
        # Local Send File Implementation
        path = os.path.expanduser(args.strip().strip("'\""))
        if not os.path.exists(path): return print(f"{Colors.F}[X] No existe.{Colors.E}")

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

        # Targets
        targets = []
        if self.ctype == 'GROUP':
             for ip, d in PEERS.items():
                 if cid in d.get('chats', set()): targets.append(ip)
        else:
             targets.append(self.remote)
        
        if not targets:
             print(f"{Colors.F}[X] Nadie en el chat.{Colors.E}")
             return

        print(f"{Colors.W}[⇧] Enviando '{n}' ({s} bytes)...{Colors.E}")
        cnt = 0
        for ip in targets:
             if ip == MY_IP: continue
             try:
                 pkt = build_packet("FILE_TRANSFER", n, s, f_hash, file_type)
                 # Manual TCP Connect/Send
                 k = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                 k.settimeout(2)
                 k.connect((ip, TCP_PORT))
                 k.send(pkt)
                 time.sleep(0.1)
                 with open(to_send_path, "rb") as f:
                     while True:
                         d = f.read(BUFFER)
                         if not d: break
                         k.sendall(d)
                 k.close()
                 cnt += 1
             except Exception as e:
                 print(f"Err Send {ip}: {e}")
        
        print(f"{Colors.G}[✔] Enviado a {cnt}.{Colors.E}")
        if is_dir and os.path.exists(to_send_path): os.remove(to_send_path)

    def leave_sess(self, cid):
        print(f"{Colors.W}[*] Saliendo...{Colors.E}")
        self.forward("--exit") # Notify lobby
        time.sleep(0.5)
        os._exit(0)

    def shutdown_app(self): self.leave_sess(None) # Child exit

    def handle_accept(self, cid): self.forward("--aceptar")
    def handle_deny(self, cid): self.forward("--rechazar")
    
    def get_var(self, name):
         if name == 'visible': return True # Dummy
         if name == 'pop_on': return not self.pop_off
         return None

    def get_active_chats(self): return {self.cid: self.get_chat(self.cid)}
    def get_version_str(self): return APP_VERSION
    
    def show_contacts(self, cid): self.forward("--contactos")
    def show_global_status(self, cid): self.forward("--estados-globales")

    def toggle_debug(self):
        self.debug = not self.debug
        return self.debug


def join_grp(gid, gp, remote_ip, my_nick, my_status, update_peers_func):
    """
    Logic to search/join group UDP in Child.
    """
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); u.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    pkt = build_packet("SEARCH_GROUP", gid, gp, my_nick, my_status)
    u.sendto(pkt, ('255.255.255.255', UDP_PORT)); u.close()

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
            p = msg.split(SEP, 3)
            cmd = p[0]
            
            if cmd == "FWD_MSG":
                if len(p) >= 4:
                    cid, tag, text = p[1], p[2], p[3]
                    if cid == MY_CHILD_ID:
                        print(f"{tag}: {text}") 
                        lock_state['last_rx'] = time.time()

            elif cmd == "MSG_IN": # v38.5 support direct msg injection
                # MSG_IN SEP sender SEP msg SEP color
                 if len(p) >= 4:
                     # Just print message
                     print(f"{p[3]}{p[1]}: {p[2]}{Colors.E}" if len(p)>3 else f"{p[2]}")

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
    
    # Adapter
    adapter = ChildAdapter(cid, myport, remote, ctype, rnick)

    signal.signal(signal.SIGINT, lambda s, f: adapter.leave_sess(cid))
    
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
            
            # --- Modular Processing ---
            # Try gw_cmd first
            
            if inp.startswith("-"):
                 # Check if CHAT_PRIV needs explicit forwarding logic bypass?
                 # Adapter handles find_global -> None
                 # gw_cmd calls adapter functions.
                 gw_cmd.process(inp, cid, adapter)
                 continue

            # --- Chat Messages ---
            if ctype == 'GROUP':
                 # Use gw_comm.send_cmd_all? No, GRP_MSG is sent to SPECIFIC GROUP ID via Multicast?
                 # No, version 37 uses `send_cmd_all` (Broadcast UDP) for GRP_MSG ??
                 # Check original code: `send_cmd_all("GRP_MSG", remote, inp)`
                 # Yes, it broadcasts to everyone "GRP_MSG <GID> <TEXT>". Everyone filters.
                 # V2: GRP_MSG | MPP | GID | TEXT
                 gw_comm.send_cmd_all("GRP_MSG", adapter.get_mpp(), remote, inp)
            else:
                 # Private Message: TCP
                 # `send_all` in original was complex. It iterated peers.
                 # Here we just send to `remote` IP.
                 gw_comm.send_tcp_packet(remote, inp.encode())

        except KeyboardInterrupt:
             adapter.leave_sess(cid)
        except Exception as e:
            print(f"{Colors.F}Error Child: {e}{Colors.E}")
