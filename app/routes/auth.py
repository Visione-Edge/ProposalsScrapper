"""Authentication routes: login, logout."""

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..auth import (
    authenticate,
    clear_failed_attempts,
    clear_session,
    create_session,
    generate_csrf_token,
    is_ip_locked,
    record_failed_attempt,
    verify_csrf_token,
    verify_session,
)
from ..state import limiter, templates

router = APIRouter()
auth_logger = logging.getLogger("auth")

LOGIN_ERROR_MESSAGES = {
    "invalid": "Usuario o contraseña incorrectos",
    "expired": "Tu sesión ha expirado",
    "csrf": "Token de seguridad inválido. Intenta de nuevo.",
    "rate": "Demasiados intentos. Intenta de nuevo en unos minutos.",
}


def _login_error(request: Request, message: str, status_code: int = 401):
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": message, "csrf_token": csrf_token},
        status_code=status_code,
    )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    if verify_session(request):
        return RedirectResponse("/", status_code=302)
    error_message = LOGIN_ERROR_MESSAGES.get(error, "")
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error_message, "csrf_token": csrf_token},
    )


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    username: str = Form(max_length=254),
    password: str = Form(max_length=128),
    csrf_token: str = Form(default=""),
):
    client_ip = request.client.host if request.client else "unknown"

    # 1. Verify CSRF first
    if not verify_csrf_token(csrf_token):
        auth_logger.warning("CSRF inválido desde IP %s", client_ip)
        return _login_error(request, "Token de seguridad inválido. Intenta de nuevo.", 403)

    # 2. Then validate fields
    if not username.strip() or not password:
        return _login_error(request, "Usuario o contraseña incorrectos")

    # 3. Check IP lockout
    if is_ip_locked(client_ip):
        auth_logger.warning("IP bloqueada por intentos excesivos: %s", client_ip)
        return _login_error(request, "Demasiados intentos fallidos. Intenta de nuevo más tarde.", 429)

    # 4. Authenticate
    if authenticate(username, password):
        auth_logger.info("Login exitoso para usuario desde IP %s", client_ip)
        clear_failed_attempts(client_ip)
        response = RedirectResponse("/", status_code=302)
        create_session(response, username)
        response.delete_cookie("csrf_token")
        return response

    record_failed_attempt(client_ip)
    auth_logger.warning("Intento de login fallido desde IP %s", client_ip)
    return _login_error(request, "Usuario o contraseña incorrectos")


@router.post("/logout")
async def logout(request: Request):
    response = RedirectResponse("/login", status_code=302)
    clear_session(response, request)
    return response
