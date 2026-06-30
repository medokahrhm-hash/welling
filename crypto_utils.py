# crypto_utils.py
#
# ملاحظة مهمة عن الفرق عن النسخة الأصلية:
# مكتبة "cryptography" تعتمد على Rust + OpenSSL bindings، وبناؤها لأندرويد
# عبر python-for-android معقد وغير مستقر دائماً.
# لذلك استبدلناها بـ "pycryptodome" التي لها recipe جاهز وموثوق في p4a
# وتعطي نفس مستوى الأمان (AES-256).

import os
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

SALT = b"nexus_core_static_salt_v1"  # ثابت لإعادة اشتقاق نفس المفتاح من نفس كلمة المرور


def _derive_key(password: str) -> bytes:
    # اشتقاق مفتاح 32 بايت (AES-256) من كلمة المرور عبر PBKDF2
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), SALT, 100_000, dklen=32)


def encrypt_file_data(file_path: str, password: str) -> bool:
    try:
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return False
        key = _derive_key(password)
        with open(file_path, "rb") as f:
            data = f.read()

        nonce = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_CTR, nonce=nonce[:8])
        encrypted = cipher.encrypt(data)

        with open(file_path, "wb") as f:
            f.write(nonce[:8] + encrypted)  # نخزن الـ nonce في بداية الملف لفك التشفير لاحقاً
        return True
    except Exception:
        return False


def decrypt_file_data(file_path: str, password: str) -> bool:
    try:
        if not os.path.exists(file_path) or os.path.isdir(file_path):
            return False
        key = _derive_key(password)
        with open(file_path, "rb") as f:
            raw = f.read()

        nonce, encrypted = raw[:8], raw[8:]
        cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
        decrypted = cipher.decrypt(encrypted)

        with open(file_path, "wb") as f:
            f.write(decrypted)
        return True
    except Exception:
        return False
