"""Password hashing and JWT tokens.

- bcrypt turns a password into a one-way hash. Even we cannot read the password back.
- A JWT is a signed "ticket" the server gives you after login. You show it on each request.
"""
import datetime as dt
import os
import secrets

import bcrypt
import jwt

# Set SECRET_KEY in your environment for real use. If missing we generate a random
# one, which is safe but logs everyone out whenever the server restarts.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "60"))


def _to_bytes(password: str) -> bytes:
    # bcrypt only looks at the first 72 bytes.
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(user_id: int) -> str:
    expires = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int | None:
    """Returns the user id, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
