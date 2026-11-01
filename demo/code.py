"""Code à usage unique d'un compte de démonstration.

    python3 demo/code.py 318264B
    docker run --rm -v "$PWD/demo:/demo:ro" python:3.12-slim python /demo/code.py 318264B
"""

import base64
import hashlib
import hmac
import json
import struct
import sys
import time
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit(__doc__)

secrets = json.loads((Path(__file__).parent / "secrets-otp.json").read_text(encoding="utf-8"))
m = sys.argv[1].lower()
if m not in secrets:
    sys.exit(f"{sys.argv[1]} n'est pas un compte de démonstration.")
cle = secrets[m].encode()
pas = int(time.time()) // 30
h = hmac.new(cle, struct.pack(">Q", pas), hashlib.sha1).digest()
o = h[-1] & 0x0F
code = (struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000
reste = 30 - int(time.time()) % 30
print(f"{code:06d}  (valable encore {reste} s)")
print(f"Clé pour une application d'authentification : {base64.b32encode(cle).decode().rstrip('=')}")
