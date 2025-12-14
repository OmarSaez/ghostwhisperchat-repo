import subprocess
import platform
import time
import threading

class PopupManager:
    def __init__(self):
        self.pop_on = True
        self.banned_ips = {} # {ip: expiry_timestamp}
        self.history = {}    # {ip: [timestamp, ...]}
        
        # Constants
        self.SPAM_WINDOW = 1.0  # seconds
        self.SPAM_LIMIT = 3     # messages
        self.BAN_DURATION = 60  # seconds

    def set_active(self, active):
        self.pop_on = active

    def _check_spam(self, ip):
        if not ip: return True
        
        now = time.time()
        
        # 1. Check Ban
        if ip in self.banned_ips:
            if now < self.banned_ips[ip]:
                return False # Still banned
            else:
                del self.banned_ips[ip] # Expired
                
        # 2. Update History
        if ip not in self.history: self.history[ip] = []
        self.history[ip].append(now)
        
        # Prune old
        self.history[ip] = [t for t in self.history[ip] if now - t <= self.SPAM_WINDOW]
        
        # 3. Check Limit
        if len(self.history[ip]) >= self.SPAM_LIMIT:
            # BAN
            self.banned_ips[ip] = now + self.BAN_DURATION
            self.history[ip] = [] # Reset history
            return False
            
        return True

    def show_notification(self, title, text, source_ip=None, force=False):
        """
        Muestra notificación no bloqueante.
        Respeta mute (--popno) y Anti-Spam.
        force=True ignora mute y spam.
        """
        # Checks
        if not force:
            if not self.pop_on: return
            if source_ip and not self._check_spam(source_ip): return

        # Launch
        self._launch_zenity(["--info", "--text", text, "--title", title, "--width=350"])

    def show_question(self, title, text, on_yes, on_no, force=True):
        """
        Muestra pregunta interactiva (Aceptar/Rechazar).
        force=True por defecto (Invitaciones suelen ser importantes).
        Corre en hilo separado.
        """
        # Checks? Usually invites bypass mute
        if not force and not self.pop_on: return
        
        def _task():
            cmd = ["zenity", "--question", "--text", text, "--title", title, 
                   "--ok-label=Aceptar", "--cancel-label=Rechazar", "--width=400"]
            ret = self._launch_zenity(cmd, wait=True)
            
            if ret == 0:
                if on_yes: on_yes()
            elif ret == 1:
                if on_no: on_no()
                
        threading.Thread(target=_task, daemon=True).start()

    def _launch_zenity(self, args, wait=False):
        """Helper para ejecutar zenity (Linux) o simulador (Windows)"""
        if platform.system() == "Linux":
            full_cmd = ["zenity"] + args
            try:
                if wait:
                    return subprocess.call(full_cmd, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(full_cmd, stderr=subprocess.DEVNULL)
            except: pass
        else:
            # TODO: Windows Implementation if needed
            pass
        return -1

# Singleton Instance
POP = PopupManager()
