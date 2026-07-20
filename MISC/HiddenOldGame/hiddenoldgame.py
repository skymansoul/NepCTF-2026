
import hashlib
from Crypto.Cipher import AES

# 问题1：可执行文件名(包含扩展名)
FILENAME = "".lower()

# 问题2：该文件的HASH(自动运算，无需填写)

# ---- ANSWER SHEET OVER ------
DATA = open(FILENAME,"rb").read()
FILEHASH = hashlib.blake2b(DATA).digest()
HASH1 = hashlib.blake2b(FILENAME.encode()).digest()
HASH2 = FILEHASH

D = hashlib.blake2b(HASH1 + HASH2).digest()
KEY = D[0:16]
IV = D[16:32]
cipher = AES.new(KEY,AES.MODE_GCM,IV)


C = bytes.fromhex('ec9f0a650c4aa727c328aa77ef05312d1df48f67aa3e86570ba107de42ee663055e279541acf5375d14f21ce949bab2d3e46401104c7f1e636')
H = bytes.fromhex('bbe86c0017179bd8aa146aff509c5f3a')
FLAG = cipher.decrypt_and_verify(C,H)
print(FLAG.decode())