"""FastAPI web app — SICOP Tender Monitor."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi.errors import RateLimitExceeded
from starlette.staticfiles import StaticFiles

from .auth import verify_session
from .routes.auth import router as auth_router
from .routes.scan import router as scan_router
from .routes.settings import router as settings_router
from .routes.tenders import router as tenders_router
from .scheduler import setup_scheduler
from .state import BASE_DIR, limiter, scan_state, templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler(scan_state, BASE_DIR)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.state.limiter = limiter

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

# Routes
app.include_router(auth_router)
app.include_router(tenders_router)
app.include_router(settings_router)
app.include_router(scan_router)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Demasiados intentos. Intenta de nuevo en unos minutos."}, status_code=429)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "Demasiados intentos. Intenta de nuevo en unos minutos.",
            "csrf_token": "",
        },
        status_code=429,
    )


_API_UNSAFE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


@app.middleware("http")
async def require_auth(request: Request, call_next):
    if request.url.path == "/login" or request.url.path.startswith("/static"):
        return await call_next(request)
    if not verify_session(request):
        if request.url.path != "/" and "text/html" not in request.headers.get("accept", ""):
            return Response(status_code=401)
        return RedirectResponse("/login", status_code=302)
    # CSRF protection for API endpoints via custom header
    if request.url.path.startswith("/api/") and request.method in _API_UNSAFE_METHODS:
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JSONResponse({"error": "Forbidden"}, status_code=403)
    return await call_next(request)
