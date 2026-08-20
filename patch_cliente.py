import sys
path = "/home/omar/Escritorio/ghostwhisperchat-repo/ghostwhisperchat_pkg/usr/lib/ghostwhisperchat/cliente.py"
with open(path, "r") as f:
    content = f.read()

target = """                     if line.strip().startswith("__SYNC_USERS__"):
                          data = line.strip().replace("__SYNC_USERS__", "", 1).strip()
                          if data:
                              # Formato: nick1,nick2,nick3
                              users = data.split(",")
                              for u in users:
                                  if u: helper.known_users.add(u.strip())
                          continue"""

replacement = """                     if line.strip().startswith("__SYNC_USERS__"):
                          data = line.strip().replace("__SYNC_USERS__", "", 1).strip()
                          if data:
                              # Formato: nick1,nick2,nick3
                              users = data.split(",")
                              for u in users:
                                  if u: helper.known_users.add(u.strip())
                          continue
                          
                     # RECEIVE NATIVE IMG (v3.038)
                     if line.strip().startswith("__NATIVE_IMG__"):
                          img_path = line.strip().replace("__NATIVE_IMG__", "", 1).strip()
                          import shutil, subprocess
                          kitty_success = False
                          if shutil.which("kitty"):
                              try:
                                  helper.print_incoming(f"{C.CYAN}[IMAGEN NATIVA]{C.RESET}")
                                  subprocess.run(["kitty", "+kitten", "icat", "--align", "left", img_path])
                                  kitty_success = True
                              except: pass
                          if not kitty_success:
                              try:
                                  helper.print_incoming(f"{C.CYAN}[IMAGEN ASCII]{C.RESET}")
                                  res = imagen_ascii.render_ascii(img_path, 60)
                                  if not res.startswith("ERROR:"):
                                      print(res)
                                  else:
                                      helper.print_incoming(f"{C.RED}[X] {res}{C.RESET}")
                              except Exception as e:
                                  helper.print_incoming(f"{C.RED}[X] Crash Rendering: {e}{C.RESET}")
                          continue"""

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w") as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Target not found")
