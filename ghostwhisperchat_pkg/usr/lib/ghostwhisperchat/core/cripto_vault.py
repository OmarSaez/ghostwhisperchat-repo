import os
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VAULT_DIR = os.path.expanduser("~/.config/gwc")
VAULT_FILE = os.path.join(VAULT_DIR, "vault.enc")
SALT_FILE = os.path.join(VAULT_DIR, ".vault.salt")

def _get_machine_id():
    for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
    return "unknown-machine-id"

def _get_key():
    os.makedirs(VAULT_DIR, mode=0o700, exist_ok=True)
    if not os.path.exists(SALT_FILE):
        salt = os.urandom(32)
        with open(SALT_FILE, "wb") as f:
            f.write(salt)
        os.chmod(SALT_FILE, 0o600)
    else:
        with open(SALT_FILE, "rb") as f:
            salt = f.read()

    machine_id = _get_machine_id()
    user_id = str(os.getuid())
    password = (machine_id + user_id).encode()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    # Return AES-256-GCM key (32 bytes)
    return kdf.derive(password)

def load_vault():
    if not os.path.exists(VAULT_FILE):
        return {}
    try:
        key = _get_key()
        aesgcm = AESGCM(key)
        
        with open(VAULT_FILE, "rb") as file:
            encrypted_data_with_nonce = file.read()
            
        # Extract nonce (12 bytes) and ciphertext
        nonce = encrypted_data_with_nonce[:12]
        ciphertext = encrypted_data_with_nonce[12:]
        
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(decrypted_data.decode('utf-8'))
    except Exception:
        return {}

def save_vault(data):
    try:
        key = _get_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12) # 96-bit nonce for GCM
        
        plaintext = json.dumps(data).encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        with open(VAULT_FILE, "wb") as file:
            file.write(nonce + ciphertext)
            
        os.chmod(VAULT_FILE, 0o600)
    except Exception as e:
        pass

def get_vault_entry(uid):
    vault = load_vault()
    return vault.get(uid, {})

def update_vault_entry(uid, ip=None, onion=None):
    vault = load_vault()
    entry = vault.get(uid, {})
    
    # Do not overwrite with None if already present
    if ip is not None:
        entry["ip"] = ip
    if onion is not None:
        entry["onion"] = onion
        
    if entry:
        vault[uid] = entry
        save_vault(vault)

def delete_vault_entry(uid):
    vault = load_vault()
    if uid in vault:
        del vault[uid]
        save_vault(vault)

def clear_vault():
    save_vault({})
