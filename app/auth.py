"""Autenticación simple de un solo usuario via cookie firmada."""

from __future__ import annotations

import os

import bcrypt
from fastapi import Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion-por-favor")
COOKIE_NAME = "sicop_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 días

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def get_credentials() -> tuple[str, str]:
    username = os.environ.get("SICOP_USERNAME", "admin")
    password_hash = os.environ.get("SICOP_PASSWORD_HASH", "")
    return username, password_hash


def authenticate(username: str, password: str) -> bool:
    valid_user, password_hash = get_credentials()
    if username != valid_user:
        return False
    if not password_hash:
        # Sin hash configurado: comparar con SICOP_PASSWORD en texto plano (solo dev)
        plain = os.environ.get("SICOP_PASSWORD", "")
        return bool(plain and password == plain)
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_session(response: Response) -> None:
    token = _serializer.dumps({"auth": True})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
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
