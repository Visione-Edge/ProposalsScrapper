"""Scan API routes."""

import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..scheduler import trigger_scan
from ..state import BASE_DIR, limiter, scan_state

router = APIRouter()

_PROGRESS_PATH = Path(BASE_DIR) / "data" / "scan_progress.json"


def _save_progress(data: dict) -> None:
    try:
        _PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_PROGRESS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@router.post("/api/scan")
@limiter.limit("2/hour")
async def start_scan(request: Request):
    days_back = None
    if request.headers.get("content-type") == "application/json":
        try:
            body = await request.json()
            if isinstance(body, dict) and isinstance(body.get("days"), int):
                days_back = max(1, min(body["days"], 30))
        except Exception:
            pass
    started = trigger_scan(scan_state, BASE_DIR, days_back=days_back)
    if not started:
        return JSONResponse({"status": "already_running"}, status_code=409)
    return {"status": "started"}


@router.get("/api/scan/status")
async def scan_status():
    data = {
        "running": scan_state["running"],
        "error": scan_state["error"],
        "last_result": scan_state["last_result"],
        "log": scan_state["log"][-10:],
    }
    _save_progress(data)
    return data
