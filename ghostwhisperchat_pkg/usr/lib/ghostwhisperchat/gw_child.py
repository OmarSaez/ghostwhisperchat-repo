
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
try: import readline
except: pass

import gw_comm
from gw_comm import PKT_PREFIX, SEP, TAG_MARK, LEN_MARK, UDP_PORT, TCP_PORT, build_packet
import gw_shared
from gw_shared import Colors, COMMAND_DEFS, resolve_cmd, IPC_PORT, get_ip, calculate_file_hash, APP_VERSION, normalize_str
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
    def __init__(self, cid, port, remote, ctype, rnick, password=None):
        self.cid = cid
        self.port = port
        self.remote = remote
        self.ctype = ctype
        self.remote_nick_init = rnick
        self.password = password
        self.pop_off = False
        self.debug = False

# ... (Previous methods)

    def _resolve_target(self, t):
        if "." in t and len(t.split(".")) == 4: return t
        t_norm = normalize_str(t)
        for ip, p in PEERS.items():
             if normalize_str(p.get('nick', '')) == t_norm: return ip
        return None

    def invite_users(self, args_str, cid):
        targets = args_str.replace(",", " ").split()
        print(f"{Colors.C}[*] Enviando invitaciones...{Colors.E}")
        sys.stdout.flush()
        
        # 1. Identify missing targets
        missing = False
        for t in targets:
             if not self._resolve_target(t): 
                 missing = True; break
        
        # 2. Auto-Scan if needed (Transparent Fix)
        if missing:
             # print(f"{Colors.C}[*] Sincronizando red...{Colors.E}")
             self.scan_network(cid, silent=True)
             time.sleep(2.0) # Wait for UDP/IPC
        
        # 3. Final Process
        for t in targets:
             target_ip = self._resolve_target(t)
             
             if target_ip:
                 inv_type = "PRIV"
                 extras = []
                 if self.ctype == 'GROUP':
                      inv_type = "GROUP"
                      gid = str(self.remote)
                      gp = str(self.password) if self.password else ""
                      extras = [gid, gp]
                 
                 # gw_comm expects business args. But build_packet adds My MPP.
                 # Actually, Lobby usually expects [MPP, Type, Args...]. 
                 # If gw_comm.send_cmd(ip, CMD, *args) -> build_packet(CMD, *args) -> CMD|MPP|Args.
                 # So MPP is indeed First Arg.
                 # Wait. Lobby handler for INVITE (Line 2200 ghostwhisperchat):
                 # if cmd_name == "INVITE": 
                 #     itype = args[1]
                 # Args[0] is MPP (sender).
                 # So gw_comm.send_cmd(target_ip, "INVITE", inv_type, *extras) RESULTS IN:
                 # INVITE | SenderMPP | inv_type | extras...
                 # THIS IS CORRECT structure according to gw_comm.
                 # SO WHY DID IT FAIL with NoneType?
                 # Maybe SenderMPP was None? Or args[1] failed?
                 # If gw_comm.send_cmd adds MPP automatically. 
                 # Let's check gw_comm.build_packet again (Step 1881):
                 # return f"{cmd_name}{SEP}{len(valid_args)}" + payload.
                 # IT DOES NOT ADD MPP!!!!
                 # I misread Step 1881. Lines 75-79.
                 # So I MUST parse get_mpp() manually.
                 gw_comm.send_cmd(target_ip, "INVITE", self.get_mpp(), inv_type, *extras)
                 print(f"{Colors.G}[➜] Invitación enviada a {t} ({target_ip}){Colors.E}")
             else:
                 print(f"{Colors.R}[X] No encontrado: {t}. (Prueba escanear primero){Colors.E}")
        sys.stdout.flush()

    def reply(self, msg, cid):
        print(msg)

    def forward(self, cmd):
        # Forward to Lobby (IPC_PORT)
        send_ipc(f"FWD_CMD{SEP}{self.cid}{SEP}{cmd}", IPC_PORT)

    # --- Methods required by gw_cmd ---
    def create_group(self, id, pas): self.forward(f"--chatgrupal {id} {pas}")
    
    def find_global(self, args):
        t_norm = normalize_str(args)
        for ip, p in PEERS.items():
             if normalize_str(p.get('nick', '')) == t_norm: return ip
        return None# Actually gw_cmd checks if t: ... else reply "Eres tu".
        # If I return None, gw_cmd does nothing?
        # NO, gw_cmd logic for CHAT_PRIV calls find_global.
        # If Child types --chatpersonal, it should probably be forwarded to Lobby which handles window spawning.
        # But gw_cmd will try to run local logic.
        # I should probably just forward CHAT_PRIV command entirely in process loop or here?
        pass

    def invite_priv(self, ip, nick, status): self.forward(f"--chatpersonal {ip}") # Helper
    

    def scan_network(self, cid, silent=False):
        if not silent: print(f"{Colors.C}[*] Escaneando red...{Colors.E}")
        sys.stdout.flush()
        # WHOIS sends IAM_HERE response from others.
        gw_comm.send_cmd_all("WHOIS", self.get_mpp())  
        
        # Wait for responses
        time.sleep(3)
        
        # Only show table if not silent
        if not silent: self.show_contacts(cid)

    def leave_sess(self, cid):
        # Implementation of Strict Disconnection Protocols
        if self.ctype == 'GROUP':
             # 1. SALIR DE GRUPO (LEAVE_GROUP)
             gid = str(self.remote)
             gp = str(self.password) if self.password else ""
             
             # Broadcast (General)
             gw_comm.send_cmd_all("LEAVE_GROUP", self.get_mpp(), gid, gp)
             
             # Redundancy: Unicast to all known peers (Fix for UDP Broadcast drops)
             for ip in PEERS:
                 gw_comm.send_cmd(ip, "LEAVE_GROUP", self.get_mpp(), gid, gp)
             
        elif self.ctype == 'PRIV':
             # 2. CERRAR PRIVADO (CLOSE_PRIV)
             gw_comm.send_cmd(self.remote, "CLOSE_PRIV", self.get_mpp(), "User Quit")

        print(f"\n{Colors.R}[!] Cerrando sesión...{Colors.E}")
        sys.stdout.flush()
        time.sleep(1)
        os._exit(0)

    def show_contacts(self, cid):
        print(f"{Colors.G}--- CONTACTOS LOCALES ---{Colors.E}")
        if not PEERS:
             print(f"{Colors.W}No hay contactos detectados.{Colors.E}")
        for ip, d in PEERS.items():
            print(f" - {d.get('nick', '?')} ({ip})")
        sys.stdout.flush()

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

    def show_ls(self, cid): self.show_contacts(cid)
    
    def set_config(self, key, val):
        # Some configs are local (pop_off), others global (nick, status)
        if key == 'nick': 
            self.forward(f"--nombre {val}")
        elif key == 'status': 
            self.forward(f"--estado {val}")

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

def print_incoming_msg(msg):
    """Prints a message while preserving the user's current input line"""
    buf = ""
    try:
        if 'readline' in sys.modules:
            buf = readline.get_line_buffer()
    except: pass
    
    # CR + Clear Line + Msg + NL
    sys.stdout.write(f"\r\033[K{msg}\n")
    
    # Restore Prompt + Buffer
    sys.stdout.write(f"{PROMPT}{buf}")
    sys.stdout.flush()

def ipc_listen_child(sock, lock_state):
    global MY_CHILD_ID, PEERS
    # Socket already bound in main thread to avoid race condition
    u = sock
    
    while True:
        try:
            d, _ = u.recvfrom(8192); msg = d.decode()
            p = msg.split(SEP, 3)
            # ... rest of loop ...
            cmd = p[0]
            
            if cmd == "FWD_MSG":
                if len(p) >= 4:
                    cid, tag, text = p[1], p[2], p[3]
                    if cid == MY_CHILD_ID:
                        print_incoming_msg(f"{tag}: {text}")
                        lock_state['last_rx'] = time.time()

            elif cmd == "MSG_IN": # v38.5 support direct msg injection
                  # MSG_IN SEP sender SEP msg SEP color
                   if len(p) >= 3:
                       # Build Message String
                       msg_str = f"{p[3]}{p[1]}: {p[2]}{Colors.E}" if len(p) > 3 else f"{p[2]}"
                       print_incoming_msg(msg_str)


            elif cmd == "CMD_ADD_PEER":
                # CMD_ADD_PEER|IP|Nick
                if len(p) >= 3:
                    pip, pnick = p[1], p[2]
                    if pip not in PEERS:
                        PEERS[pip] = {'nick': pnick, 'chats': {MY_CHILD_ID}}
                        # Silent connection to avoid interrupting user typing
                        # print(f"\r{Colors.G}[+] Conectado con {pnick} ({pip}){Colors.E}")
                        # refresh_prompt()
                    else:
                         PEERS[pip]['chats'].add(MY_CHILD_ID)

            elif cmd == "FWD_FILE":
                if len(p) >= 4 and p[1] == MY_CHILD_ID:
                    print_incoming_msg(f"{Colors.W}[⇩] Archivo '{p[3]}' de {p[2]} recibido en Lobby.{Colors.E}")
            
            elif cmd == "FWD_PEER":
                if len(p) >= 4:
                    rmt_ip, rmt_nick, rmt_stat = p[1], p[2], p[3]
                    if rmt_ip not in PEERS: PEERS[rmt_ip] = {'nick': rmt_nick, 'chats': {MY_CHILD_ID}}
                    else: 
                         if isinstance(PEERS[rmt_ip], dict):
                             PEERS[rmt_ip]['nick'] = rmt_nick
                             PEERS[rmt_ip]['chats'].add(MY_CHILD_ID)
                    print_incoming_msg(f"{Colors.G}[+] Detectado: {rmt_nick}{Colors.E}")
            
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
    adapter = ChildAdapter(cid, myport, remote, ctype, rnick, password)

    signal.signal(signal.SIGINT, lambda s, f: adapter.leave_sess(cid))
    
    # Shared State for Popups
    pop_state = {'last_input': 0, 'last_rx': time.time(), 'pop_off': False, 'type': ctype, 'remote_id': remote, 'remote_nick': rnick}

    # Header
    if ctype == 'GROUP':
        header_txt = f"== CHAT GRUPAL {remote} =="
        set_terminal_title(f"GRUP {remote}")
    else:
        header_txt = f"== CHAT PRIVADO CON {rnick} =="
        set_terminal_title(f"PRIV {rnick}")
        
    print(f"{Colors.H}{header_txt}{Colors.E}")
    
    # Start IPC (Bind in Main Thread to catch Sync Response)
    try:
        ipc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ipc_sock.bind(('127.0.0.1', int(myport)))
    except Exception as e:
        print(f"Error fatal IPC bind: {e}")
        return

    threading.Thread(target=ipc_listen_child, args=(ipc_sock, pop_state), daemon=True).start()
    
    # Request Initial Peer Sync from Lobby
    send_ipc(f"CMD_SYNC_PEERS{SEP}{cid}", IPC_PORT)
    
    # Start Logic
    if ctype == 'GROUP':
        # join_grp just sends the SEARCH packet
        threading.Thread(target=join_grp, args=(remote, password, remote, MY_NICK, MY_STATUS, None), daemon=True).start()
        # Auto-Scan network to populate peers immediately (Smart Feature)
        adapter.scan_network(cid, silent=True)
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
                 # V2: MSJ GRUP Unicast Mesh TCP (Port 44496)
                 mpp = adapter.get_mpp()
                 gid = remote
                 pkid = str(int(time.time()))
                 pkt = gw_comm.build_msj(mpp, "GRUP", [pkid, gid], inp)
                 
                 sent_count = 0
                 for ip, pdata in PEERS.items():
                      if cid in pdata.get('chats', set()):
                           gw_comm.send_tcp_packet(ip, pkt, gw_comm.TCP_PORT_GRP)
                           sent_count += 1
                 if sent_count == 0:
                     print(f"{Colors.W}[!] No hay nadie más en el grupo.{Colors.E}")
                 
                 # Notify Lobby of Activity (Smart Pop)
                 send_ipc(f"CMD_ACTIVITY{SEP}{cid}", IPC_PORT)

            else:
                 # Private Message: TCP
                 mpp = adapter.get_mpp()
                 pkt = gw_comm.build_msj(mpp, "PRIV", [], inp)
                 gw_comm.send_tcp_packet(remote, pkt)
                 
                 # Notify Lobby of Activity (Smart Pop)
                 send_ipc(f"CMD_ACTIVITY{SEP}{cid}", IPC_PORT)

        except KeyboardInterrupt:
             adapter.leave_sess(cid)
        except Exception as e:
            print(f"{Colors.F}Error Child: {e}{Colors.E}")
