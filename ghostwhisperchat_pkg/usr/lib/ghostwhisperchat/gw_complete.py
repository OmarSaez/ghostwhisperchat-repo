import readline
import difflib
import sys
from gw_shared import Colors, resolve_cmd, COMMAND_DEFS

class ProbabilisticCompleter:
    def __init__(self, context_provider):
        self.context_provider = context_provider 
        
    def get_all_commands(self):
        cmds = []
        for k, v in COMMAND_DEFS.items():
            cmds.append(f"--{k.lower()}")
            for alias in v.get('aliases', []):
                 if alias.startswith('--'): cmds.append(alias)
        return cmds

    def suggest_command(self, invalid_cmd):
        all_cmds = self.get_all_commands()
        matches = difflib.get_close_matches(invalid_cmd, all_cmds, n=3, cutoff=0.55)
        return matches

    def suggest_user(self, invalid_user):
        ctx = self.context_provider()
        candidates = set()
        for u in ctx.get('known_users', {}).values(): candidates.add(u.get('nick', '?'))
        for p in ctx.get('peers', {}).values(): candidates.add(p.get('nick', '?'))
        
        for line in ctx.get('scan_buffer', []):
             try:
                 if "Detectado:" in line:
                     parts = line.split("Detectado:")[1].strip().split('(')
                     nick = parts[0].strip()
                     candidates.add(nick)
             except: pass

        matches = difflib.get_close_matches(invalid_user, list(candidates), n=5, cutoff=0.55)
        return matches

    def complete(self, text, state):
        buffer = readline.get_line_buffer()
        line_parts = buffer.lstrip().split()
        options = []
        is_cmd = not line_parts or (len(line_parts) == 1 and not buffer.endswith(' '))
        
        if is_cmd:
             all_cmds = self.get_all_commands()
             if text:
                 # 1. Prefijo exacto (PRIORIDAD ABSOLUTA)
                 # Evita que coincidencias lejanas rompan el prefijo común (TAB)
                 opts = [c for c in all_cmds if c.startswith(text)]
                 
                 # 2. Si no hay prefijos, usar Fuzzy
                 if not opts:
                     opts = difflib.get_close_matches(text, all_cmds, n=5, cutoff=0.50)
                 
                 options = opts
             else:
                 options = all_cmds

        else:
             cmd_str = line_parts[0]
             cmd_key = resolve_cmd(cmd_str)
             
             if cmd_key in ['INVITE', 'CHAT_PRIV']:
                  ctx = self.context_provider()
                  candidates = set()
                  for u in ctx.get('known_users', {}).values(): candidates.add(u.get('nick', '?'))
                  for p in ctx.get('peers', {}).values(): candidates.add(p.get('nick', '?'))
                  if 'scan_buffer' in ctx:
                       for line in ctx['scan_buffer']:
                           if "Detectado:" in line:
                               try:
                                   nick = line.split("Detectado:")[1].strip().split('(')[0].strip()
                                   candidates.add(nick)
                               except: pass
                  cand_list = list(candidates)
                  if text:
                      # 1. Prefijo
                      opts = [c for c in cand_list if c.startswith(text)]
                      # 2. Fuzzy fallback
                      if not opts:
                          opts = difflib.get_close_matches(text, cand_list, n=5, cutoff=0.55)
                      options = opts
                  else:
                      options = cand_list
                      
        if state < len(options):
            return options[state]
        else:
            return None

COMPLETER = None

def setup(context_provider):
    global COMPLETER
    try:
        COMPLETER = ProbabilisticCompleter(context_provider)
        readline.set_completer(COMPLETER.complete)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims(' \t\n,')
        return True
    except Exception as e:
        print(f"Error init completer: {e}")
        return False
