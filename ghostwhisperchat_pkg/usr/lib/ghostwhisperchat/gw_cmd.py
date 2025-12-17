
import time
import os
import uuid
import platform
import subprocess
import shutil
import json
import threading

import gw_shared
from gw_shared import Colors, COMMAND_DEFS, resolve_cmd, IPC_PORT
import gw_comm
from gw_comm import SEP

# Helper for formatted listing in LS
def _build_members_list(adapter, cid):
    cdata = adapter.get_chat(cid)
    if not cdata: return None
    
    my_nick, my_ip, _ = adapter.get_my_info()
    
    members = []
    members.append(f"{Colors.BO}> {my_nick} ({my_ip}) [Tú]{Colors.E}")
    
    ctype = cdata.get('type')
    
    if ctype == 'PRIV':
        rid = cdata['remote_id']
        rnick = cdata.get('remote_nick', '?')
        members.append(f"- {rnick} ({rid})")
    
    elif ctype == 'GROUP':
        # We need PEERS from adapter
        peers = adapter.get_peers()
        count = 1
        for ip, pdata in peers.items():
            if isinstance(pdata, dict) and cid in pdata.get('chats', set()):
                members.append(f"- {pdata.get('nick', '?')} ({ip})")
                count += 1
        
        return members, count
        
    return members, 2

def process(inp, origin_cid, adapter):
    """
    Procesa un comando.
    inp: String linea de comando (ej: --ls)
    origin_cid: ID del chat si viene de hijo, None si es Lobby
    adapter: Objeto Adptador (LobbyAdapter o ChildAdapter)
    """
    inp = inp.strip()
    if not inp: return

    parts = inp.split(" ", 1)
    raw_cmd = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    
    # Resolver
    cmd_key = resolve_cmd(raw_cmd)
    
    # Legacy Support
    if not cmd_key:
         if inp in ["--log on"]: cmd_key = 'LOG_ON'
         elif inp in ["--log off"]: cmd_key = 'LOG_OFF'

    # --- DISPATCHER ---
    
    if cmd_key == 'CHAT_GROUP':
        gp_parts = args.split()
        if len(gp_parts) == 2:
            adapter.create_group(gp_parts[0], gp_parts[1])
            adapter.reply(f"{Colors.G}[*] Grupo creado/unido.{Colors.E}", origin_cid)
        else: 
            adapter.reply(f"{Colors.F}El formato es ID CLAVE. Ejemplo: --chatgrupal 10 clave123.{Colors.E}", origin_cid)

    elif cmd_key == 'CHAT_PRIV':
        t = adapter.find_global(args)
        if t:
            my_nick, my_ip, my_st = adapter.get_my_info()
            if t == my_ip: 
                adapter.reply(f"{Colors.F}Eres tú.{Colors.E}", origin_cid)
            else:
                adapter.reply(f"{Colors.W}[*] Invitando...{Colors.E}", origin_cid)
                adapter.invite_priv(t, my_nick, my_st)
        else:
            if hasattr(adapter, 'suggest_user'): adapter.suggest_user(args)
            else: adapter.reply(f"{Colors.F}Usuario no encontrado.{Colors.E}", origin_cid)

    elif cmd_key == 'LS':
         if origin_cid:
             # Logic for child LS
             res = _build_members_list(adapter, origin_cid)
             if not res: return
             members, count = res
             
             msg = f"{Colors.H}--- MIEMBROS DEL GRUPO ({count}) ---{Colors.E}\n" + "\n".join(members)
             
             # If Adapter is Child, it just prints. If Adapter is Lobby, it sends IPC.
             # Adapter.reply handles abstraction?
             # But LS output format is specific.
             # Let's assume adapter.reply can handle multiline.
             # Only discrepancy: Lobby logic used `send_ipc("MSG_IN"...)`
             # Child logic prints directly.
             adapter.reply(msg, origin_cid)
             return

         # Logic for Lobby LS
         adapter.show_lobby_summary()

    elif cmd_key == 'CONTACTS':
        adapter.show_contacts(origin_cid)

    elif cmd_key == 'SCAN': adapter.scan_network(origin_cid)
    
    elif cmd_key == 'SCAN_VIS_ON':
        adapter.set_config('visible', True)
        adapter.reply(f"{Colors.G}[✔] Visible en escáner.{Colors.E}", origin_cid)
        
    elif cmd_key == 'SCAN_VIS_OFF':
        adapter.set_config('visible', False)
        adapter.reply(f"{Colors.W}[✔] Oculto en escáner.{Colors.E}", origin_cid)

    elif cmd_key == 'STATUS':
        adapter.set_config('status', args)
        adapter.reply(f"{Colors.G}[✔] Estado actualizado.{Colors.E}", origin_cid)
        adapter.broadcast_status(args)

    elif cmd_key == 'NICK':
        old_nick, _, _ = adapter.get_my_info()
        adapter.set_config('nick', args)
        my_nick, _, _ = adapter.get_my_info() # Refetch updated
        
        msg = f"{Colors.G}[✔] Nick cambiado de {old_nick} a {my_nick}.{Colors.E}"
        adapter.reply(msg, origin_cid)
        adapter.broadcast_status() # Uses new nick automatically
        adapter.update_title()

    elif cmd_key == 'LOG_ON': 
        adapter.set_config('log_on', True)
        adapter.reply(f"{Colors.G}LOG ON - Historial activado.{Colors.E}", origin_cid)
        
    elif cmd_key == 'LOG_OFF': 
        adapter.set_config('log_on', False)
        adapter.reply(f"{Colors.W}LOG OFF - Historial desactivado.{Colors.E}", origin_cid)
        
    elif cmd_key == 'POP_OFF': 
        adapter.set_config('pop_on', False)
        adapter.reply(f"{Colors.W}Mute Manual.{Colors.E}", origin_cid)
        
    elif cmd_key == 'POP_ON': 
        adapter.set_config('pop_on', True)
        adapter.reply(f"{Colors.G}Popups ON.{Colors.E}", origin_cid)
    
    elif cmd_key == 'DL_ON':
        adapter.set_config('auto_dl', True)
        adapter.reply(f"{Colors.G}[✔] Descarga automática ACTIVADA.{Colors.E}", origin_cid)
        
    elif cmd_key == 'DL_OFF':
        adapter.set_config('auto_dl', False)
        adapter.reply(f"{Colors.W}[✔] Descarga automática DESACTIVADA (Se preguntará).{Colors.E}", origin_cid)

    elif cmd_key == 'AUTOSTART_ON': adapter.toggle_autostart(True, origin_cid)
    elif cmd_key == 'AUTOSTART_OFF': adapter.toggle_autostart(False, origin_cid)
    
    elif cmd_key == 'VERSION':
        ver_str = gw_shared.APP_VERSION
        adapter.reply(f"{Colors.G}GhostWhisperChat {ver_str}{Colors.E}", origin_cid)

    elif cmd_key == 'INTEGRITY':
        if hasattr(adapter, 'check_integrity'):
            adapter.check_integrity(origin_cid)
        else:
            adapter.reply(f"{Colors.F}Este entorno no soporta test de integridad.{Colors.E}", origin_cid)

    elif cmd_key == 'CLEAR':
        adapter.clear_screen(origin_cid)

    elif cmd_key == 'INVITE':
        if not origin_cid:
             adapter.reply(f"{Colors.F}[!] Comando disponible solo dentro de una ventana de chat.{Colors.E}", origin_cid)
        else:
             adapter.invite_users(args, origin_cid)

    elif cmd_key == 'FILE':
         if not origin_cid:
             adapter.reply(f"{Colors.F}[!] Envío de archivos disponible solo dentro de una ventana de chat.{Colors.E}", origin_cid)
         else:
             if args: adapter.send_file(args, origin_cid)
             else: adapter.reply(f"{Colors.F}Falta ruta del archivo.{Colors.E}", origin_cid)

    elif cmd_key == 'EXIT':
        if origin_cid:
            adapter.leave_sess(origin_cid)
        else:
            adapter.shutdown_app()

    elif cmd_key == 'ACCEPT':
        adapter.handle_accept(origin_cid)

    elif cmd_key == 'DENY':
        adapter.handle_deny(origin_cid)

    elif cmd_key == 'HELP':
        show_help(adapter, origin_cid)

    elif cmd_key == 'SHORTCUTS':
        show_shortcuts(adapter, origin_cid)
        
    elif cmd_key == 'GLOBAL_STATUS':
        adapter.show_global_status(origin_cid)

    elif cmd_key == 'DEBUG':
        is_dbg = adapter.toggle_debug()
        status = "ACTIVADO" if is_dbg else "DESACTIVADO"
        adapter.reply(f"{Colors.M}[DEBUG] Modo Debug {status}.{Colors.E}", origin_cid)

    elif cmd_key is None and raw_cmd.startswith("-"):
          if hasattr(adapter, 'suggest_command'):
               adapter.suggest_command(raw_cmd)
          else:
               adapter.reply(f"{Colors.F}Comando desconocido: {raw_cmd}. Prueba --help o --ab.{Colors.E}", origin_cid)


# --- HELPERS (Moving from main) ---

def show_help(adapter, target_cid=None):
    lines = []
    lines.append(f" {Colors.BO}--- AYUDA Y COMANDOS ---{Colors.E}")
    
    cats = {
        "GESTIÓN DE CHATS": [
            ("--chatpersonal (Nick y/o IP)", "Crear un chat privado con un usuario."),
            ("--chatgrupal ID CLAVE", "Unirse/Crear sala."), 
            ("--invite (Nick1, Nick2...) y/o IPs", "Invitar gente al grupo actual."),
            ("--aceptar / --rechazar", "Responder a invitaciones pendientes."),
            ("--ls", "Listar usuarios CONECTADOS en el chat."), 
            ("--salir", "Desconectar de la sesión.")
        ],
        "RED Y CONTACTOS": [
            ("--quienes", "Escanear red (¿Quién está online?)."),
            ("--contactos", "Ver historial de gente vista."),
            ("--quienes-si / --quienes-no", "Visibilidad en escáner.")
        ],
        "UTILIDADES Y ARCHIVOS": [
            ("--archivo (Ruta)", "Enviar archivo."),
            ("--nombre (NuevoNick)", "Cambiar tu nombre visible."),
            ("--estado (Texto)", "Cambiar estado."),
            ("--estados-globales", "Ver resumen de configuración."),
            ("--abreviaciones", "Ver todos los formatos aceptados por cada comando."),
            ("--limpiar", "Limpiar pantalla.")
        ],
        "SISTEMA Y CONFIGURACIÓN": [
             ("--log on / off", "Guardar historial."),
             ("--descarga-si / --descarga-no", "Control descarga automática."),
             ("--integridad", "Ver integridad del servicio.")
        ]
    }

    for cat_name, cmds in cats.items():
        lines.append(f"\n {Colors.C}:: {cat_name} ::{Colors.E}")
        for c, d in cmds: 
            lines.append(f"   {Colors.BO}{c:<35}{Colors.E} : {d}")

    lines.append("-" * 60)
    adapter.reply("\n".join(lines), target_cid)

def show_shortcuts(adapter, target_cid=None):
    msg_lines = [f"{Colors.H}=== ABREVIACIONES Y ALIAS ==={Colors.E}", ""]
    for key in sorted(COMMAND_DEFS.keys()):
        data = COMMAND_DEFS[key]
        aliases = data['aliases']
        desc = data['desc']
        msg_lines.append(f"{Colors.BO}● {key}{Colors.E} : {desc}")
        msg_lines.append(f"   ↳ Variantes: { Colors.C + ', '.join(aliases) + Colors.E }")
        msg_lines.append("")
    adapter.reply("\n".join(msg_lines), target_cid)

def show_global_status(adapter, target_cid=None):
    my_nick, my_ip, my_st = adapter.get_my_info()
    vis = adapter.get_var("visible")
    auto_dl = adapter.get_var("auto_dl")
    log_on = adapter.get_var("log_on")
    ver = adapter.get_version_str()
    users = adapter.get_known_users()
    chats = adapter.get_active_chats()

    lines = [f"{Colors.H}=== ESTADO GLOBAL DEL SISTEMA ==={Colors.E}"]
    lines.append(f" {Colors.BO}Versión:{Colors.E} {ver}")
    lines.append(f" {Colors.BO}Usuario:{Colors.E} {my_nick} ({my_ip})")
    lines.append(f" {Colors.BO}Estado:{Colors.E} {my_st}")
    lines.append(f" {Colors.BO}Visibilidad Red:{Colors.E} {'VISIBLE' if vis else 'OCULTO'}")
    lines.append(f" {Colors.BO}Auto-Descargas:{Colors.E} {'ACTIVADAS' if auto_dl else 'OFF'}")
    lines.append(f" {Colors.BO}Guardar Historial:{Colors.E} {'ON' if log_on else 'OFF'}")
    
    # AutoStart (assume adapter handles logic or returns N/A string)
    # Simplified
    
    lines.append("")
    lines.append(f"{Colors.BO}:: LISTADO DE CONTACTOS ({len(users)}) ::{Colors.E}")
    for ip, d in users.items():
         seen = time.strftime('%H:%M', time.localtime(d['t']))
         lines.append(f" - {d['nick']} ({ip}) [{d['status']}] (Visto: {seen})")
         
    lines.append("")
    lines.append(f"{Colors.BO}:: CHATS ACTIVOS ({len(chats)}) ::{Colors.E}")
    for cid, d in chats.items():
         lines.append(f" - [{cid}] {d['type']}: {d.get('remote_nick', d['remote_id'])}")

    adapter.reply("\n".join(lines), target_cid)
