"""Settings routes: keyword configuration."""

import yaml
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ..auth import generate_csrf_token, verify_csrf_token
from ..state import BASE_DIR, templates

router = APIRouter()


def _load_keywords() -> dict:
    keywords_path = BASE_DIR / "keywords.yaml"
    with open(keywords_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_keywords(data: dict) -> None:
    keywords_path = BASE_DIR / "keywords.yaml"
    with open(keywords_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, saved: str = ""):
    keywords = _load_keywords()
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "kw": keywords, "saved": saved == "1", "csrf_token": csrf_token},
    )


@router.post("/settings")
async def settings_save(
    request: Request,
    alta: str = Form(default=""),
    media: str = Form(default=""),
    baja: str = Form(default=""),
    csrf_token: str = Form(default=""),
):
    if not verify_csrf_token(csrf_token):
        return RedirectResponse("/settings", status_code=302)

    def parse_keywords(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    _save_keywords({
        "alta": parse_keywords(alta),
        "media": parse_keywords(media),
        "baja": parse_keywords(baja),
    })
    return RedirectResponse("/settings?saved=1", status_code=302)
