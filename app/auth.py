"""Autenticación simple de un solo usuario via cookie firmada."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import OrderedDict

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
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "5"))
CSRF_MAX_AGE = 600  # 10 minutos
LOCKOUT_THRESHOLD = 15
LOCKOUT_DURATION = 900  # 15 minutos

_serializer = URLSafeTimedSerializer(SECRET_KEY)

# Hash pre-calculado para mantener timing constante cuando el username es inválido.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode()

# --- Session Store ---
_sessions_lock = threading.Lock()
_active_sessions: OrderedDict[str, dict] = OrderedDict()  # session_id -> {username, created_at}

# --- Failed Login Tracking ---
_failed_lock = threading.Lock()
_failed_attempts: dict[str, list[float]] = {}  # ip -> [timestamps]


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


# --- Session Management ---

def _cleanup_expired_sessions() -> None:
    """Remove expired sessions from the store. Must be called with _sessions_lock held."""
    now = time.time()
    expired = [sid for sid, data in _active_sessions.items()
               if now - data["created_at"] > COOKIE_MAX_AGE]
    for sid in expired:
        del _active_sessions[sid]


def create_session(response: Response, username: str) -> None:
    session_id = secrets.token_hex(16)
    with _sessions_lock:
        _cleanup_expired_sessions()
        # Evict oldest sessions if at limit
        while len(_active_sessions) >= MAX_SESSIONS:
            _active_sessions.popitem(last=False)
        _active_sessions[session_id] = {
            "username": username,
            "created_at": int(time.time()),
        }
    token = _serializer.dumps({
        "session_id": session_id,
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


def clear_session(response: Response, request: Request | None = None) -> None:
    if request:
        token = request.cookies.get(COOKIE_NAME)
        if token:
            try:
                data = _serializer.loads(token, max_age=COOKIE_MAX_AGE)
                session_id = data.get("session_id")
                if session_id:
                    with _sessions_lock:
                        _active_sessions.pop(session_id, None)
            except (BadSignature, SignatureExpired):
                pass
    response.delete_cookie(COOKIE_NAME)


def verify_session(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        data = _serializer.loads(token, max_age=COOKIE_MAX_AGE)
        session_id = data.get("session_id")
        if not session_id:
            return False
        with _sessions_lock:
            return session_id in _active_sessions
    except (BadSignature, SignatureExpired):
        return False


# --- CSRF (HMAC-signed tokens, no cookie needed) ---

def generate_csrf_token() -> str:
    """Generate an HMAC-signed CSRF token bound to SECRET_KEY."""
    nonce = secrets.token_hex(16)
    timestamp = str(int(time.time()))
    payload = f"{nonce}:{timestamp}"
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{nonce}:{timestamp}:{sig}"


def verify_csrf_token(token: str) -> bool:
    """Verify an HMAC-signed CSRF token."""
    if not token:
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    nonce, timestamp_str, sig = parts
    try:
        ts = int(timestamp_str)
    except ValueError:
        return False
    if time.time() - ts > CSRF_MAX_AGE:
        return False
    payload = f"{nonce}:{timestamp_str}"
    expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


# --- Failed Login Tracking ---

def is_ip_locked(ip: str) -> bool:
    """Check if an IP is locked out due to too many failed attempts."""
    with _failed_lock:
        attempts = _failed_attempts.get(ip, [])
        now = time.time()
        recent = [t for t in attempts if now - t < LOCKOUT_DURATION]
        _failed_attempts[ip] = recent
        return len(recent) >= LOCKOUT_THRESHOLD


def record_failed_attempt(ip: str) -> None:
    """Record a failed login attempt for an IP."""
    with _failed_lock:
        if ip not in _failed_attempts:
            _failed_attempts[ip] = []
        _failed_attempts[ip].append(time.time())


def clear_failed_attempts(ip: str) -> None:
    """Clear failed attempts for an IP after successful login."""
    with _failed_lock:
        _failed_attempts.pop(ip, None)
