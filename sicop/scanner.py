"""Lógica central del scan — compartida entre CLI y web app."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml

from .classifier import Classification, RelevanceClassifier
from .notifier import send_discord, send_email_contract_updates, send_email_new_tenders, send_slack
from .storage import Storage
from sources import get_enabled_sources
from sources.base import SOURCE_LABELS

logger = logging.getLogger(__name__)

_TODAY = datetime.now().strftime("%Y-%m-%d")


def _is_expired(tender) -> bool:
    """True if the tender is no longer active."""
    end = getattr(tender, "bid_end_date", "")
    if end and len(end) >= 10 and end[:10] < _TODAY:
        return True
    # If no deadline, check if registration is older than 6 months
    reg = getattr(tender, "registration_date", "")
    if reg and len(reg) >= 10:
        try:
            reg_dt = datetime.strptime(reg[:10], "%Y-%m-%d")
            if (datetime.now() - reg_dt).days > 180:
                return True
        except ValueError:
            pass
    return False

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
    """Ejecuta el scan de todas las fuentes habilitadas y retorna un resumen."""

    def log(msg: str) -> None:
        logger.info(msg)
        if progress_cb:
            progress_cb(msg)

    cfg = load_config(base_dir)
    db_path = base_dir / cfg.get("database", "data/licitaciones.db")
    keywords_path = base_dir / "keywords.yaml"
    procedure_types = cfg.get("procedure_types", []) or []
    institutions_filter = cfg.get("institutions", []) or []
    _days = days_back if days_back is not None else cfg.get("days_back", 3)
    min_relevance = cfg.get("notify_min_relevance", "media")

    classifier = RelevanceClassifier(keywords_path)
    enabled_sources = get_enabled_sources(cfg)

    if not enabled_sources:
        log("No hay fuentes habilitadas")
        return {"fetched": 0, "new": 0, "new_relevant": 0, "contract_updates": 0,
                "total_in_db": 0, "by_source": {},
                "completed_at": datetime.now().isoformat(timespec="seconds")}

    log(f"Fuentes habilitadas: {', '.join(SOURCE_LABELS.get(s, s) for s, _ in enabled_sources)}")

    all_new_relevant: list[tuple] = []
    all_contract_updates: list = []
    total_fetched = 0
    total_new = 0
    by_source: dict[str, dict] = {}

    with Storage(db_path) as storage:
        known_ids = storage.get_known_ids()
        log(f"Licitaciones en DB: {len(known_ids)}")

        for source_name, client in enabled_sources:
            label = SOURCE_LABELS.get(source_name, source_name)
            log(f"Escaneando {label} (últimos {_days} días)...")

            try:
                # SICOP has extra params
                if source_name == "sicop":
                    tenders = client.fetch_recent_tenders(
                        days_back=_days,
                        max_pages=max_pages,
                        procedure_types=procedure_types or None,
                        institutions=institutions_filter or None,
                    )
                else:
                    tenders = client.fetch_recent_tenders(days_back=_days)
            except Exception as e:
                log(f"Error escaneando {label}: {e}")
                by_source[source_name] = {"fetched": 0, "new": 0, "error": str(e)}
                continue
            finally:
                client.close()

            log(f"{label}: {len(tenders)} licitaciones obtenidas")

            source_new = 0
            for tender in tenders:
                if _is_expired(tender):
                    continue

                classification = classifier.classify_tender(tender)
                if classification.level == "no_relevante":
                    continue

                is_new = (tender.cartel_no, tender.cartel_seq) not in known_ids

                if not is_new and _is_contract_status(tender.status):
                    meta = storage.get_tender_meta(tender.cartel_no, tender.cartel_seq)
                    if meta and meta["favorite"] and not _is_contract_status(meta["status"]):
                        all_contract_updates.append(tender)

                storage.upsert_tender(tender, classification.level, classification.matched_keywords)

                if is_new:
                    source_new += 1
                    known_ids.add((tender.cartel_no, tender.cartel_seq))
                    if classification.meets_minimum(min_relevance):
                        all_new_relevant.append((tender, classification))

            total_fetched += len(tenders)
            total_new += source_new
            by_source[source_name] = {"fetched": len(tenders), "new": source_new}

        stats = storage.get_stats()

    log(f"Total — Nuevas: {total_new} | Relevantes nuevas: {len(all_new_relevant)}")

    if send_notifications:
        notif_cfg = cfg.get("notifications", {})
        slack_cfg = notif_cfg.get("slack", {})
        if all_new_relevant and slack_cfg.get("enabled") and slack_cfg.get("webhook_url"):
            try:
                send_slack(slack_cfg["webhook_url"], all_new_relevant)
                log("Notificación Slack enviada")
            except Exception as e:
                log(f"Error Slack: {e}")

        discord_cfg = notif_cfg.get("discord", {})
        if all_new_relevant and discord_cfg.get("enabled") and discord_cfg.get("webhook_url"):
            try:
                send_discord(discord_cfg["webhook_url"], all_new_relevant)
                log("Notificación Discord enviada")
            except Exception as e:
                log(f"Error Discord: {e}")

        email_cfg = notif_cfg.get("email", {})
        if email_cfg.get("enabled"):
            if all_new_relevant and email_cfg.get("notify_on_new", True):
                try:
                    send_email_new_tenders(email_cfg, all_new_relevant)
                    log("Notificación email enviada")
                except Exception as e:
                    log(f"Error email nuevas: {e}")
            if all_contract_updates and email_cfg.get("notify_on_contract", True):
                try:
                    send_email_contract_updates(email_cfg, all_contract_updates)
                    log(f"Notificación email contratos enviada ({len(all_contract_updates)})")
                except Exception as e:
                    log(f"Error email contratos: {e}")

    return {
        "fetched": total_fetched,
        "new": total_new,
        "new_relevant": len(all_new_relevant),
        "contract_updates": len(all_contract_updates),
        "total_in_db": stats["total"],
        "by_source": by_source,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }
