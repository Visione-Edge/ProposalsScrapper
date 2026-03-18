"""Scheduler de scans automáticos con APScheduler."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from sicop.scanner import run_scan

logger = logging.getLogger(__name__)

_scan_lock = threading.Lock()


def _load_schedule(base_dir: Path) -> dict:
    p = base_dir / "config.yaml"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("schedule", {})
    return {}


def setup_scheduler(scan_state: dict, base_dir: Path) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="America/Costa_Rica")

    def scheduled_scan() -> None:
        if scan_state["running"]:
            logger.info("Scan ya en ejecución, saltando scheduled run")
            return
        logger.info("Iniciando scan programado")
        _do_scan(scan_state, base_dir)

    sched = _load_schedule(base_dir)
    hour = sched.get("hour", 7)
    minute = sched.get("minute", 0)
    days = sched.get("days", "mon-fri")

    scheduler.add_job(
        scheduled_scan,
        CronTrigger(hour=hour, minute=minute, day_of_week=days),
        id="daily_scan",
        replace_existing=True,
    )
    logger.info("Scan programado: %s:%02d dias=%s (America/Costa_Rica)", hour, minute, days)
    return scheduler


def _do_scan(scan_state: dict, base_dir: Path, days_back: int | None = None) -> None:
    scan_state["running"] = True
    scan_state["error"] = None
    scan_state["log"] = []

    def on_progress(msg: str) -> None:
        scan_state["log"].append(msg)

    try:
        result = run_scan(
            base_dir=base_dir,
            days_back=days_back,
            send_notifications=True,
            progress_cb=on_progress,
        )
        scan_state["last_result"] = result
    except Exception as e:
        logger.exception("Error en scan")
        scan_state["error"] = "Error interno durante el escaneo. Revisa los logs del servidor."
    finally:
        scan_state["running"] = False


def trigger_scan(scan_state: dict, base_dir: Path, days_back: int | None = None) -> bool:
    """Lanza un scan manual en un thread separado. Retorna False si ya hay uno corriendo."""
    with _scan_lock:
        if scan_state["running"]:
            return False
        scan_state["running"] = True
    thread = threading.Thread(
        target=_do_scan, args=(scan_state, base_dir, days_back), daemon=True
    )
    thread.start()
    return True
