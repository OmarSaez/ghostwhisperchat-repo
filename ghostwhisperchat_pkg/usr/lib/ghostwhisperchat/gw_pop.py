import subprocess
import platform
import time
import threading

class PopupManager:
    def __init__(self):
        self.pop_on = True
        # Legacy Spam Filter Removed (Handled by Lobby Smart Logic)

    def set_active(self, active):
        self.pop_on = active

    def show_notification(self, title, text, duration=5, force=False):
        """
        Muestra notificación visual.
        Usamos zenity --info con timeout para que se cierre sola.
        """
        if not force and not self.pop_on: return

        # Launch Zenity Info with Timeout
        args = ["--info", "--text", text, "--title", title, "--width=350", f"--timeout={duration}"]
        self._launch_zenity(args)

    def show_question(self, title, text, on_yes, on_no, force=True, timeout=0):
        """
        Muestra pregunta interactiva (Aceptar/Rechazar).
        """
        if not force and not self.pop_on: return
        
        def _task():
            cmd = ["--question", "--text", text, "--title", title, 
                   "--ok-label=Aceptar", "--cancel-label=Rechazar", "--width=400"]
            if timeout > 0: cmd.append(f"--timeout={timeout}")
            
            ret = self._launch_zenity(cmd, wait=True)
            
            if ret == 0:
                if on_yes: on_yes()
            elif ret == 1:
                # Zenity returns 1 for Cancel/No
                if on_no: on_no()
            else:
                 # Timeout or error
                 if on_no: on_no()
                
        threading.Thread(target=_task, daemon=True).start()

    def _launch_zenity(self, args, wait=False):
        """Helper para ejecutar zenity (Linux)"""
        # Remove 'zenity' from args if passed, add only once
        full_cmd = ["zenity"] + args
        
        if platform.system() == "Linux":
            try:
                if wait:
                    return subprocess.call(full_cmd, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(full_cmd, stderr=subprocess.DEVNULL)
            except: pass
        else:
            # Placeholder Windows
            pass
        return -1

# Singleton Instance
POP = PopupManager()

# Module Level Exports for Ease of Use
def show(title, text, duration=10):
    POP.show_notification(title, text, duration=duration)

def ask(title, text, on_yes, on_no):
    POP.show_question(title, text, on_yes, on_no)

def set_active(val):
    POP.set_active(val)
