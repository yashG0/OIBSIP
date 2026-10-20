import hashlib
import hmac
import secrets

from chat_app.database import ChatDatabase

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_KEY_BYTES = 32


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    salt = secrets.token_bytes(_SALT_BYTES)
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_KEY_BYTES,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, key_hex = stored_hash.split("$")
        if algorithm != "scrypt":
            return False

        expected = bytes.fromhex(key_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except ValueError, TypeError:
        return False


class AuthService:
    def __init__(self, database: ChatDatabase) -> None:
        self.database = database

    def register(self, username: str, password: str) -> int:
        username = username.strip()
        if not username or len(username) > 32:
            raise ValueError("Username must be 1–32 characters.")
        return self.database.create_user(username, hash_password(password))

    def login(self, username: str, password: str) -> bool:
        user = self.database.get_user(username)
        if user is None:
            return False
        return verify_password(password, user["password_hash"])
