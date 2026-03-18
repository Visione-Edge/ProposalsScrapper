"""FastAPI web app para el Monitor de Licitaciones SICOP."""

from __future__ import annotations

import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from sicop.storage import Storage

from .auth import authenticate, clear_session, create_session, verify_session
from .scheduler import setup_scheduler, trigger_scan

BASE_DIR = Path(__file__).parent.parent

# ── Logging ──────────────────────────────────────────────────────────────────
auth_logger = logging.getLogger("auth")

# ── Rate Limiting ────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Mensajes de error predefinidos ───────────────────────────────────────────
LOGIN_ERROR_MESSAGES = {
    "invalid": "Usuario o contraseña incorrectos",
    "expired": "Tu sesión ha expirado",
    "csrf": "Token de seguridad inválido. Intenta de nuevo.",
    "rate": "Demasiados intentos. Intenta de nuevo en unos minutos.",
}

scan_state: dict = {
    "running": False,
    "error": None,
    "last_result": None,
    "log": [],
}


def get_config() -> dict:
    p = BASE_DIR / "config.yaml"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_storage() -> Storage:
    cfg = get_config()
    db_path = BASE_DIR / cfg.get("database", "data/licitaciones.db")
    return Storage(db_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler(scan_state, BASE_DIR)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


# ── Rate limit exception handler ────────────────────────────────────────────
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "Demasiados intentos. Intenta de nuevo en unos minutos.",
        },
        status_code=429,
    )


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.middleware("http")
async def require_auth(request: Request, call_next):
    if request.url.path == "/login":
        return await call_next(request)
    if not verify_session(request):
        return RedirectResponse("/login", status_code=302)
    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    error_message = LOGIN_ERROR_MESSAGES.get(error, "")
    csrf_token = secrets.token_hex(32)
    response = templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error_message, "csrf_token": csrf_token},
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=True,
        samesite="strict",
        max_age=600,
    )
    return response


@app.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    username: str = Form(max_length=254),
    password: str = Form(max_length=128),
    csrf_token: str = Form(default=""),
):
    client_ip = request.client.host if request.client else "unknown"

    # Validar que username y password no estén vacíos
    if not username.strip() or not password:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Usuario o contraseña incorrectos",
                "csrf_token": secrets.token_hex(32),
            },
            status_code=401,
        )

    # Verificar CSRF token (Double Submit Cookie pattern)
    cookie_csrf = request.cookies.get("csrf_token", "")
    if not csrf_token or not cookie_csrf or csrf_token != cookie_csrf:
        auth_logger.warning(f"Intento de login fallido desde IP {client_ip}")
        new_csrf = secrets.token_hex(32)
        response = templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Token de seguridad inválido. Intenta de nuevo.",
                "csrf_token": new_csrf,
            },
            status_code=403,
        )
        response.set_cookie(
            key="csrf_token",
            value=new_csrf,
            httponly=True,
            samesite="strict",
            max_age=600,
        )
        return response

    if authenticate(username, password):
        auth_logger.info(f"Login exitoso para usuario desde IP {client_ip}")
        resp = RedirectResponse("/", status_code=302)
        create_session(resp, username)
        resp.delete_cookie("csrf_token")
        return resp

    auth_logger.warning(f"Intento de login fallido desde IP {client_ip}")
    new_csrf = secrets.token_hex(32)
    response = templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "Usuario o contraseña incorrectos",
            "csrf_token": new_csrf,
        },
        status_code=401,
    )
    response.set_cookie(
        key="csrf_token",
        value=new_csrf,
        httponly=True,
        samesite="strict",
        max_age=600,
    )
    return response


@app.post("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    clear_session(resp)
    return resp


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    with get_storage() as storage:
        tenders = storage.get_all_tenders()
        stats = storage.get_stats()

    tenders_json = json.dumps(tenders, ensure_ascii=False, default=str)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "tenders_json": tenders_json,
            "stats": stats,
            "scan_state": scan_state,
        },
    )


# ── API — Favoritos / No interesa / Notas ─────────────────────────────────────

@app.post("/api/tender/{cartel_no}/{cartel_seq}/favorite")
async def toggle_favorite(cartel_no: str, cartel_seq: str):
    with get_storage() as storage:
        value = storage.toggle_favorite(cartel_no, cartel_seq)
    return {"favorite": value}


@app.post("/api/tender/{cartel_no}/{cartel_seq}/not-interested")
async def toggle_not_interested(cartel_no: str, cartel_seq: str):
    with get_storage() as storage:
        value = storage.toggle_not_interested(cartel_no, cartel_seq)
    return {"not_interested": value}


@app.put("/api/tender/{cartel_no}/{cartel_seq}/notes")
async def save_notes(cartel_no: str, cartel_seq: str, request: Request):
    body = await request.json()
    notes = body.get("notes", "")
    with get_storage() as storage:
        storage.save_notes(cartel_no, cartel_seq, notes)
    return {"ok": True}


@app.post("/api/tender/{cartel_no}/{cartel_seq}/viewed")
async def mark_viewed(cartel_no: str, cartel_seq: str):
    with get_storage() as storage:
        storage.mark_viewed(cartel_no, cartel_seq)
    return {"ok": True}


# ── API — Scan ────────────────────────────────────────────────────────────────

@app.post("/api/scan")
async def start_scan(request: Request):
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    days = body.get("days") if isinstance(body, dict) else None
    started = trigger_scan(scan_state, BASE_DIR, days_back=days)
    if not started:
        return JSONResponse({"status": "already_running"}, status_code=409)
    return {"status": "started"}


@app.get("/api/scan/status")
async def scan_status():
    return {
        "running": scan_state["running"],
        "error": scan_state["error"],
        "last_result": scan_state["last_result"],
        "log": scan_state["log"][-10:],
    }


# ── Configuración de keywords ─────────────────────────────────────────────────

def load_keywords() -> dict:
    p = BASE_DIR / "keywords.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_keywords(data: dict) -> None:
    p = BASE_DIR / "keywords.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, saved: str = ""):
    kw = load_keywords()
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "kw": kw, "saved": saved == "1"},
    )


@app.post("/settings")
async def settings_save(
    request: Request,
    alta: str = Form(default=""),
    media: str = Form(default=""),
    baja: str = Form(default=""),
):
    def parse(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    save_keywords({"alta": parse(alta), "media": parse(media), "baja": parse(baja)})
    return RedirectResponse("/settings?saved=1", status_code=302)
