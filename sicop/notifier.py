"""Notificaciones por webhook a Slack y Discord."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape as _esc

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


def _smtp_password(smtp_cfg: dict) -> str:
    """Gets SMTP password from config or SMTP_PASSWORD env var."""
    return smtp_cfg.get("password") or os.environ.get("SMTP_PASSWORD", "")


def send_email_new_tenders(smtp_cfg: dict, tenders: list[tuple["Tender", "Classification"]]) -> None:
    """Envía email con las licitaciones nuevas relevantes."""
    if not smtp_cfg.get("enabled") or not tenders:
        return
    recipients = smtp_cfg.get("recipients", [])
    if not recipients:
        return

    rows = ""
    for tender, classification in tenders:
        color = RELEVANCE_COLORS.get(classification.level, "#95a5a6")
        kws = _esc(", ".join(classification.matched_keywords[:5]))
        rows += f"""
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">
                <span style="background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;text-transform:uppercase">{_esc(classification.level)}</span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;color:#1d4ed8">{_esc(_truncate(tender.name, 120))}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:13px">{_esc(tender.institution_name)}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;color:#6b7280">{_esc(tender.bid_end_date or '—')}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;color:#6b7280">{kws}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;margin:0;padding:24px">
<div style="max-width:800px;margin:0 auto;background:white;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.1)">
  <div style="background:#2c3e50;padding:20px 28px">
    <h1 style="color:white;margin:0;font-size:18px">Proposals Center — Licitaciones Nuevas</h1>
    <p style="color:rgba(255,255,255,0.7);margin:6px 0 0;font-size:13px">{len(tenders)} licitacion{'es' if len(tenders)!=1 else ''} relevante{'s' if len(tenders)!=1 else ''} encontrada{'s' if len(tenders)!=1 else ''}</p>
  </div>
  <div style="padding:24px">
    <table style="width:100%;border-collapse:collapse">
      <thead><tr style="background:#f3f4f6">
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Relevancia</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Nombre</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Institución</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Fecha límite</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Keywords</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:20px;font-size:12px;color:#9ca3af">Ingresá al dashboard para ver el detalle completo y gestionar tus favoritos.</p>
  </div>
</div></body></html>"""

    subject = f"SICOP: {len(tenders)} licitacion{'es' if len(tenders)!=1 else ''} nueva{'s' if len(tenders)!=1 else ''} relevante{'s' if len(tenders)!=1 else ''}"
    _send_email(smtp_cfg, subject, html)


def send_email_contract_updates(smtp_cfg: dict, tenders: list) -> None:
    """Envía email cuando licitaciones favoritas entran en estado de contrato."""
    if not smtp_cfg.get("enabled") or not tenders:
        return
    recipients = smtp_cfg.get("recipients", [])
    if not recipients:
        return

    rows = ""
    for tender in tenders:
        rows += f"""
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-weight:600;color:#1d4ed8">{_esc(_truncate(tender.name, 120))}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:13px">{_esc(tender.institution_name)}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb">
                <span style="background:#10b981;color:white;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">{_esc(tender.status)}</span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-size:12px;color:#6b7280">{_esc(tender.inst_cartel_no)}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;margin:0;padding:24px">
<div style="max-width:700px;margin:0 auto;background:white;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.1)">
  <div style="background:#065f46;padding:20px 28px">
    <h1 style="color:white;margin:0;font-size:18px">Proposals Center — Actualización de Favoritos</h1>
    <p style="color:rgba(255,255,255,0.8);margin:6px 0 0;font-size:13px">{len(tenders)} licitacion{'es' if len(tenders)!=1 else ''} favorita{'s' if len(tenders)!=1 else ''} en estado de adjudicación/contrato</p>
  </div>
  <div style="padding:24px">
    <table style="width:100%;border-collapse:collapse">
      <thead><tr style="background:#f3f4f6">
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Nombre</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Institución</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Estado</th>
        <th style="padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;color:#6b7280">Concurso</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="margin-top:20px;font-size:12px;color:#9ca3af">Ingresá al dashboard para ver el detalle completo.</p>
  </div>
</div></body></html>"""

    subject = f"SICOP: {len(tenders)} favorito{'s' if len(tenders)!=1 else ''} {'fueron' if len(tenders)!=1 else 'fue'} adjudicado{'s' if len(tenders)!=1 else ''}"
    _send_email(smtp_cfg, subject, html)


def _send_email(smtp_cfg: dict, subject: str, html_body: str) -> None:
    host = smtp_cfg.get("host", "")
    port = int(smtp_cfg.get("port", 587))
    username = smtp_cfg.get("username", "")
    password = _smtp_password(smtp_cfg)
    recipients = smtp_cfg.get("recipients", [])

    if not (host and username and password and recipients):
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.login(username, password)
        smtp.sendmail(username, recipients, msg.as_string())
