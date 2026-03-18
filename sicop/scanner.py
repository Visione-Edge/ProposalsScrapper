"""Lógica central del scan — compartida entre CLI y web app."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml

from .classifier import Classification, RelevanceClassifier
from .client import SICOPClient, Tender
from .notifier import send_discord, send_email_contract_updates, send_email_new_tenders, send_slack
from .storage import Storage

logger = logging.getLogger(__name__)

# Status strings that indicate a tender has been awarded/contracted
_CONTRACT_STATUSES = {"adjudicado", "contratado", "en contrato", "adjudicación"}


def _is_contract_status(status: str) -> bool:
    s = status.lower()
    return any(cs in s for cs in _CONTRACT_STATUSES)


def load_config(base_dir: Path) -> dict:
    p = base_dir / "config.yaml"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def run_scan(
    base_dir: Path,
    days_back: int | None = None,
    max_pages: int = 0,
    send_notifications: bool = True,
    progress_cb: Callable[[str], None] | None = None,
) -> dict:
    """Ejecuta el scan de SICOP y retorna un resumen de resultados."""

    def log(msg: str) -> None:
        logger.info(msg)
        if progress_cb:
            progress_cb(msg)

    cfg = load_config(base_dir)
    page_size = cfg.get("page_size", 50)
    delay = cfg.get("request_delay", 1.0)
    db_path = base_dir / cfg.get("database", "data/licitaciones.db")
    keywords_path = base_dir / "keywords.yaml"
    procedure_types = cfg.get("procedure_types", []) or []
    institutions_filter = cfg.get("institutions", []) or []
    _days = days_back if days_back is not None else cfg.get("days_back", 3)
    min_relevance = cfg.get("notify_min_relevance", "media")

    classifier = RelevanceClassifier(keywords_path)

    log(f"Conectando a SICOP (últimos {_days} días)...")

    with SICOPClient(page_size=page_size, request_delay=delay) as client:
        with Storage(db_path) as storage:
            known_ids = storage.get_known_ids()
            log(f"Licitaciones en DB: {len(known_ids)}")

            tenders = client.fetch_recent_tenders(
                days_back=_days,
                max_pages=max_pages,
                procedure_types=procedure_types or None,
                institutions=institutions_filter or None,
            )
            log(f"Licitaciones obtenidas de API: {len(tenders)}")

            new_relevant: list[tuple[Tender, Classification]] = []
            contract_updates: list[Tender] = []
            new_count = 0

            for tender in tenders:
                classification = classifier.classify_tender(tender)
                if classification.level == "no_relevante":
                    continue

                is_new = (tender.cartel_no, tender.cartel_seq) not in known_ids

                # Check for contract status change on favorites before upserting
                if not is_new and _is_contract_status(tender.status):
                    meta = storage.get_tender_meta(tender.cartel_no, tender.cartel_seq)
                    if meta and meta["favorite"] and not _is_contract_status(meta["status"]):
                        contract_updates.append(tender)

                storage.upsert_tender(tender, classification.level, classification.matched_keywords)

                if is_new:
                    new_count += 1
                    if classification.meets_minimum(min_relevance):
                        new_relevant.append((tender, classification))

            stats = storage.get_stats()

    log(f"Nuevas: {new_count} | Relevantes nuevas: {len(new_relevant)}")

    if send_notifications:
        notif_cfg = cfg.get("notifications", {})
        slack_cfg = notif_cfg.get("slack", {})
        if new_relevant and slack_cfg.get("enabled") and slack_cfg.get("webhook_url"):
            try:
                send_slack(slack_cfg["webhook_url"], new_relevant)
                log("Notificación Slack enviada")
            except Exception as e:
                log(f"Error Slack: {e}")

        discord_cfg = notif_cfg.get("discord", {})
        if new_relevant and discord_cfg.get("enabled") and discord_cfg.get("webhook_url"):
            try:
                send_discord(discord_cfg["webhook_url"], new_relevant)
                log("Notificación Discord enviada")
            except Exception as e:
                log(f"Error Discord: {e}")

        email_cfg = notif_cfg.get("email", {})
        if email_cfg.get("enabled"):
            if new_relevant and email_cfg.get("notify_on_new", True):
                try:
                    send_email_new_tenders(email_cfg, new_relevant)
                    log("Notificación email enviada")
                except Exception as e:
                    log(f"Error email nuevas: {e}")
            if contract_updates and email_cfg.get("notify_on_contract", True):
                try:
                    send_email_contract_updates(email_cfg, contract_updates)
                    log(f"Notificación email contratos enviada ({len(contract_updates)})")
                except Exception as e:
                    log(f"Error email contratos: {e}")

    return {
        "fetched": len(tenders),
        "new": new_count,
        "new_relevant": len(new_relevant),
        "contract_updates": len(contract_updates),
        "total_in_db": stats["total"],
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }
