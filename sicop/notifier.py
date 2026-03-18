"""Notificaciones por webhook a Slack y Discord."""

from __future__ import annotations

import httpx

from .classifier import Classification
from .client import Tender

RELEVANCE_COLORS = {
    "alta": "#e74c3c",
    "media": "#f39c12",
    "baja": "#3498db",
}

RELEVANCE_EMOJI = {
    "alta": "\U0001f534",
    "media": "\U0001f7e0",
    "baja": "\U0001f535",
}


def _truncate(text: str, max_len: int = 200) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


def send_slack(webhook_url: str, tenders: list[tuple[Tender, Classification]]) -> None:
    """Envía notificación a Slack con las licitaciones nuevas."""
    if not webhook_url or not tenders:
        return

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"SICOP: {len(tenders)} licitaciones nuevas relevantes"},
        }
    ]

    for tender, classification in tenders[:15]:  # Slack tiene límite de bloques
        emoji = RELEVANCE_EMOJI.get(classification.level, "")
        color = RELEVANCE_COLORS.get(classification.level, "#95a5a6")
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"{emoji} *<{tender.url}|{_truncate(tender.name, 150)}>*\n"
                    f"*Institución:* {tender.institution_name}\n"
                    f"*Concurso:* {tender.inst_cartel_no}\n"
                    f"*Relevancia:* {classification.level} ({', '.join(classification.matched_keywords[:5])})\n"
                    f"*Fecha límite:* {tender.bid_end_date or 'No disponible'}"
                ),
            },
        })

    if len(tenders) > 15:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"_...y {len(tenders) - 15} más. Revisa el dashboard._"},
        })

    payload = {"blocks": blocks}
    httpx.post(webhook_url, json=payload, timeout=10.0)


def send_discord(webhook_url: str, tenders: list[tuple[Tender, Classification]]) -> None:
    """Envía notificación a Discord con las licitaciones nuevas."""
    if not webhook_url or not tenders:
        return

    embeds = []
    for tender, classification in tenders[:10]:  # Discord permite hasta 10 embeds
        color_hex = RELEVANCE_COLORS.get(classification.level, "#95a5a6")
        color_int = int(color_hex.lstrip("#"), 16)
        embeds.append({
            "title": _truncate(tender.name, 200),
            "url": tender.url,
            "color": color_int,
            "fields": [
                {"name": "Institución", "value": tender.institution_name, "inline": True},
                {"name": "Concurso", "value": tender.inst_cartel_no, "inline": True},
                {"name": "Relevancia", "value": f"{classification.level} ({', '.join(classification.matched_keywords[:3])})", "inline": True},
                {"name": "Fecha límite", "value": tender.bid_end_date or "No disponible", "inline": True},
            ],
        })

    payload = {
        "content": f"**SICOP: {len(tenders)} licitaciones nuevas relevantes**",
        "embeds": embeds,
    }

    if len(tenders) > 10:
        payload["content"] += f"\n_...y {len(tenders) - 10} más. Revisa el dashboard._"

    httpx.post(webhook_url, json=payload, timeout=10.0)
