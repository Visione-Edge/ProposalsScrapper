"""Dashboard and tender API routes."""

import json

from fastapi import APIRouter, Path, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..state import get_storage, scan_state, templates

router = APIRouter()

_ID_PATTERN = r"^[A-Za-z0-9\-]+$"


@router.get("/", response_class=HTMLResponse)
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


@router.post("/api/tender/{cartel_no}/{cartel_seq}/favorite")
async def toggle_favorite(
    cartel_no: str = Path(pattern=_ID_PATTERN, max_length=50),
    cartel_seq: str = Path(pattern=_ID_PATTERN, max_length=20),
):
    with get_storage() as storage:
        value = storage.toggle_favorite(cartel_no, cartel_seq)
    return {"favorite": value}


@router.post("/api/tender/{cartel_no}/{cartel_seq}/not-interested")
async def toggle_not_interested(
    cartel_no: str = Path(pattern=_ID_PATTERN, max_length=50),
    cartel_seq: str = Path(pattern=_ID_PATTERN, max_length=20),
):
    with get_storage() as storage:
        value = storage.toggle_not_interested(cartel_no, cartel_seq)
    return {"not_interested": value}


class NotesPayload(BaseModel):
    notes: str = Field(default="", max_length=10000)


@router.put("/api/tender/{cartel_no}/{cartel_seq}/notes")
async def save_notes(
    payload: NotesPayload,
    cartel_no: str = Path(pattern=_ID_PATTERN, max_length=50),
    cartel_seq: str = Path(pattern=_ID_PATTERN, max_length=20),
):
    with get_storage() as storage:
        storage.save_notes(cartel_no, cartel_seq, payload.notes)
    return {"ok": True}


@router.post("/api/tender/{cartel_no}/{cartel_seq}/viewed")
async def mark_viewed(
    cartel_no: str = Path(pattern=_ID_PATTERN, max_length=50),
    cartel_seq: str = Path(pattern=_ID_PATTERN, max_length=20),
):
    with get_storage() as storage:
        storage.mark_viewed(cartel_no, cartel_seq)
    return {"ok": True}
