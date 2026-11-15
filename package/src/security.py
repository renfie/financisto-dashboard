"""Multi-user TOTP helpers. Never return a token/seed in logs."""
from __future__ import annotations
import base64
import hashlib
import hmac
import io
import secrets
import struct
import time
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
import qrcode
from qrcode.image.svg import SvgPathImage


def encryption_key(app_secret: str) -> bytes:
    # app_secret is the independent, randomly generated secret from the first install.
    # Do NOT rotate it without exporting/migrating the TOTP seeds first.
    return base64.urlsafe_b64encode(hashlib.sha256(('financisto-totp-v1:' + app_secret).encode()).digest())


def encrypt_seed(seed: str, app_secret: str) -> str:
    return Fernet(encryption_key(app_secret)).encrypt(seed.encode('ascii')).decode('ascii')


def decrypt_seed(ciphertext: str, app_secret: str) -> str:
    return Fernet(encryption_key(app_secret)).decrypt(ciphertext.encode('ascii')).decode('ascii')


def new_totp_seed() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode('ascii').rstrip('=')


def totp_at(seed: str, step: int) -> str:
    key = base64.b32decode(seed.upper() + '=' * (-len(seed) % 8), casefold=True)
    digest = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0f
    number = struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7fffffff
    return str(number % 1_000_000).zfill(6)


def valid_totp_step(seed: str, code: str, last_used_step: int = -1, now: float | None = None) -> int | None:
    if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    step = int((time.time() if now is None else now) // 30)
    for candidate in (step - 1, step, step + 1):
        if candidate > last_used_step and candidate >= 0 and hmac.compare_digest(totp_at(seed, candidate), code):
            return candidate
    return None


def totp_svg_data_uri(seed: str, username: str) -> str:
    label = quote('Financisto Dashboard:' + username, safe='')
    issuer = quote('Financisto Dashboard', safe='')
    uri = f'otpauth://totp/{label}?secret={seed}&issuer={issuer}&algorithm=SHA1&digits=6&period=30'
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=5, border=3, image_factory=SvgPathImage)
    qr.add_data(uri)
    qr.make(fit=True)
    buf = io.BytesIO()
    qr.make_image().save(buf)
    return 'data:image/svg+xml;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def new_recovery_codes() -> list[str]:
    return [f'{secrets.token_hex(4)}-{secrets.token_hex(4)}' for _ in range(10)]


def recovery_hash(user_id: int, code: str) -> str:
    normalized = code.strip().replace('-', '').lower()
    return hashlib.sha256(f'financisto-recovery:{user_id}:{normalized}'.encode()).hexdigest()
