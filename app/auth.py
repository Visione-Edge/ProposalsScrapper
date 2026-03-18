"""Autenticación simple de un solo usuario via cookie firmada."""

from __future__ import annotations

import hmac
import os
import secrets
import time

import bcrypt
from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no esta configurada. "
        "Establece la variable de entorno SECRET_KEY con un valor aleatorio de al menos 32 bytes."
    )

COOKIE_NAME = "sicop_session"
COOKIE_MAX_AGE = 60 * 60 * 8  # 8 horas
SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "true").lower() != "false"

_serializer = URLSafeTimedSerializer(SECRET_KEY)

# Hash pre-calculado para mantener timing constante cuando el username es inválido.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()


def get_credentials() -> tuple[str, str]:
    username = os.environ.get("SICOP_USERNAME", "admin")
    password_hash = os.environ.get("SICOP_PASSWORD_HASH", "")
    if not password_hash:
        raise RuntimeError(
            "SICOP_PASSWORD_HASH no esta configurada. "
            "Establece la variable de entorno SICOP_PASSWORD_HASH con un hash bcrypt valido."
        )
    return username, password_hash


def authenticate(username: str, password: str) -> bool:
    valid_user, password_hash = get_credentials()
    username_ok = hmac.compare_digest(username, valid_user)
    # Siempre ejecutar bcrypt.checkpw para mantener timing constante.
    hash_to_check = password_hash if username_ok else _DUMMY_HASH
    password_ok = bcrypt.checkpw(password.encode(), hash_to_check.encode())
    return username_ok and password_ok


def create_session(response: Response, username: str) -> None:
    token = _serializer.dumps({
        "session_id": secrets.token_hex(16),
        "username": username,
        "created_at": int(time.time()),
    })
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=SECURE_COOKIES,
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def verify_session(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        _serializer.loads(token, max_age=COOKIE_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False
