
import sys
import os

lib_path = "/home/omar/Escritorio/ghostwhisperchat-repo/ghostwhisperchat_pkg/usr/lib/ghostwhisperchat"
sys.path.append(lib_path)

import gw_cmd

class MockAdapter:
    def __init__(self):
        self.cid = "TEST_CID"
    def reply(self, msg, cid):
        print(f"MOCK_REPLY [{cid}]:\n{msg}")
    def get_var(self, n): return None
    def create_group(self, id, p): pass
    def find_global(self, a): pass
    def invite_priv(self, i, n, s): pass
    def get_chat(self, c): return {'type': 'GROUP', 'remote_id': '123'}
    def get_my_info(self): return "Me", "1.2.3.4", "On"
    def get_peers(self): return {'1.2.3.5': {'nick': 'Peer1', 'chats': {'TEST_CID'}}}
    def show_lobby_summary(self): pass
    def get_known_users(self): return {}
    def scan_network(self, c): pass
    def set_config(self, k, v): pass
    def broadcast_status(self, s=None): pass
    def update_title(self): pass
    def toggle_autostart(self, v, c): pass
    def clear_screen(self, c): pass
    def invite_users(self, a, c): pass
    def send_file(self, a, c): pass
    def leave_sess(self, c): pass
    def shutdown_app(self): pass
    def handle_accept(self, c): pass
    def handle_deny(self, c): pass
    def get_active_chats(self): return {'TEST_CID': {'type': 'GROUP'}}
    def get_version_str(self): return "vTEST"
    def toggle_debug(self): return True

adapter = MockAdapter()
print(">>> TEST HELP")
gw_cmd.process("--help", "TEST_CID", adapter)
print(">>> TEST LS")
gw_cmd.process("--ls", "TEST_CID", adapter)
