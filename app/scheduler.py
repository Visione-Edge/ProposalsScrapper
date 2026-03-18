"""Scheduler de scans automáticos con APScheduler."""

from __future__ import annotations

import logging
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from sicop.scanner import run_scan

logger = logging.getLogger(__name__)


def setup_scheduler(scan_state: dict, base_dir: Path) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="America/Costa_Rica")

    def scheduled_scan() -> None:
        if scan_state["running"]:
            logger.info("Scan ya en ejecución, saltando scheduled run")
            return
        logger.info("Iniciando scan programado")
        _do_scan(scan_state, base_dir)

    # Por defecto: 7 AM hora Costa Rica, lunes a viernes
    scheduler.add_job(
        scheduled_scan,
        CronTrigger(hour=7, minute=0, day_of_week="mon-fri"),
        id="daily_scan",
        replace_existing=True,
    )
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
        scan_state["error"] = str(e)
    finally:
        scan_state["running"] = False


def trigger_scan(scan_state: dict, base_dir: Path, days_back: int | None = None) -> bool:
    """Lanza un scan manual en un thread separado. Retorna False si ya hay uno corriendo."""
    import threading

    if scan_state["running"]:
        return False
    thread = threading.Thread(
        target=_do_scan, args=(scan_state, base_dir, days_back), daemon=True
    )
    thread.start()
    return True
