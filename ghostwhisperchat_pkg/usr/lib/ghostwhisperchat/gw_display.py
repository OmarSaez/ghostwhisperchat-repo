import os
import sys
from gw_shared import Colors, APP_VERSION

class DisplayManager:
    def __init__(self, status_cb):
        self.history = []
        self.status_cb = status_cb 
        
    def add(self, text):
        if not text: return
        self.history.append(text)
        # Limit history to prevent memory bloat
        if len(self.history) > 1000: self.history.pop(0)
        
    def refresh(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        
        try:
            st = self.status_cb()
            vis_txt = f"{Colors.G}SI{Colors.E}" if st.get('visible') else f"{Colors.F}NO{Colors.E}"
            
            print(f"{Colors.H}Version: {APP_VERSION}{Colors.E}")
            print(f"Mi IP: {Colors.BO}{st.get('ip')}{Colors.E} | Nick: {Colors.BO}{st.get('nick')}{Colors.E} | Visible en red: {vis_txt} | Estado: {Colors.C}{st.get('status')}{Colors.E}")
            print(f"Total de chats: {Colors.M}{st.get('chats',0)}{Colors.E}")
            print(f"Total de contactos: {Colors.M}{st.get('contacts',0)}{Colors.E}")
            print(f"Puedes poner --help para ver los comandos")
            print(f"{Colors.G}Bienvenido al lobby{Colors.E}")
            print("-" * 60)
            
            for line in self.history:
                print(line)
                
        except Exception as e:
            print(f"Error repainting UI: {e}")
            # Fallback dump
            for line in self.history: print(line)

# Global Instance Placeholder
DISPLAY = None
