import sys
path = "/home/omar/Escritorio/ghostwhisperchat-repo/ghostwhisperchat_pkg/usr/lib/ghostwhisperchat/cliente.py"
with open(path, "r") as f:
    content = f.read()

target = """                              try:
                                 helper.print_incoming(f"{C.CYAN}[IMAGEN NATIVA]{C.RESET}")
                                 subprocess.run(["kitty", "+kitten", "icat", "--align", "left", img_path])
                                 kitty_success = True
                             except: pass"""

replacement = """                              try:
                                 helper.print_incoming(f"{C.CYAN}[IMAGEN NATIVA]{C.RESET}")
                                 helper.pause_input = True
                                 subprocess.run(["kitty", "+kitten", "icat", "--align", "left", img_path])
                                 import time
                                 time.sleep(0.4)
                                 helper.pause_input = False
                                 kitty_success = True
                             except:
                                 helper.pause_input = False"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Target not found")
