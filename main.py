#!/usr/bin/env python3
"""Monitor de Licitaciones SICOP — Costa Rica.

Consulta la API pública de SICOP, clasifica licitaciones por relevancia
para empresas de desarrollo de software, y genera alertas + dashboard.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from sicop.classifier import Classification, RelevanceClassifier
from sicop.client import SICOPClient, Tender
from sicop.dashboard import generate_dashboard
from sicop.notifier import send_discord, send_slack
from sicop.storage import Storage

console = Console()

BASE_DIR = Path(__file__).parent


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@click.group()
@click.option("--config", "config_path", default="config.yaml", help="Ruta al archivo de configuración")
@click.pass_context
def cli(ctx: click.Context, config_path: str) -> None:
    """Monitor de Licitaciones SICOP — Costa Rica."""
    ctx.ensure_object(dict)
    cfg_path = BASE_DIR / config_path
    if cfg_path.exists():
        ctx.obj["config"] = load_config(cfg_path)
    else:
        console.print(f"[yellow]Advertencia: No se encontró {cfg_path}, usando defaults.[/yellow]")
        ctx.obj["config"] = {}


@cli.command()
@click.option("--days", default=None, type=int, help="Días hacia atrás a consultar (default: 3)")
@click.option("--max-pages", default=None, type=int, help="Máximo de páginas a consultar")
@click.option("--notify/--no-notify", default=True, help="Enviar notificaciones")
@click.option("--dashboard/--no-dashboard", "gen_dashboard", default=True, help="Generar dashboard HTML")
@click.pass_context
def scan(ctx: click.Context, days: int | None, max_pages: int | None, notify: bool, gen_dashboard: bool) -> None:
    """Escanea SICOP por licitaciones nuevas y clasifica por relevancia."""
    cfg = ctx.obj["config"]

    page_size = cfg.get("page_size", 50)
    delay = cfg.get("request_delay", 1.0)
    db_path = BASE_DIR / cfg.get("database", "data/licitaciones.db")
    keywords_path = BASE_DIR / "keywords.yaml"
    dashboard_path = BASE_DIR / cfg.get("dashboard_output", "data/dashboard.html")
    procedure_types = cfg.get("procedure_types", []) or []
    institutions = cfg.get("institutions", []) or []
    mp = max_pages if max_pages is not None else cfg.get("max_pages", 0)
    days_back = days if days is not None else cfg.get("days_back", 3)

    classifier = RelevanceClassifier(keywords_path)

    console.print(f"[bold]Conectando a SICOP...[/bold] (últimos {days_back} días)")

    with SICOPClient(page_size=page_size, request_delay=delay) as client, Storage(db_path) as storage:
        known_ids = storage.get_known_ids()
        console.print(f"Licitaciones en base de datos: {len(known_ids)}")

        console.print("Descargando licitaciones recientes...")
        try:
            tenders = client.fetch_recent_tenders(
                days_back=days_back,
                max_pages=mp,
                procedure_types=procedure_types or None,
                institutions=institutions or None,
            )
        except Exception as e:
            console.print(f"[red]Error al consultar SICOP: {e}[/red]")
            sys.exit(1)

        console.print(f"Licitaciones obtenidas: {len(tenders)}")

        new_tenders: list[tuple[Tender, Classification]] = []
        new_relevant: list[tuple[Tender, Classification]] = []
        min_relevance = cfg.get("notify_min_relevance", "media")

        for tender in tenders:
            classification = classifier.classify_tender(tender)
            if classification.level == "no_relevante":
                continue

            is_new = (tender.cartel_no, tender.cartel_seq) not in known_ids
            storage.upsert_tender(tender, classification.level, classification.matched_keywords)

            if is_new:
                new_tenders.append((tender, classification))
                if classification.meets_minimum(min_relevance):
                    new_relevant.append((tender, classification))

        # Resumen en terminal
        _print_summary(new_tenders, new_relevant)

        # Dashboard
        if gen_dashboard:
            path = generate_dashboard(storage, dashboard_path)
            console.print(f"\n[green]Dashboard generado:[/green] {path}")

        # Notificaciones
        if notify and new_relevant:
            notif_cfg = cfg.get("notifications", {})
            _send_notifications(notif_cfg, new_relevant)


def _print_summary(
    new_tenders: list[tuple[Tender, Classification]],
    new_relevant: list[tuple[Tender, Classification]],
) -> None:
    """Imprime resumen de licitaciones nuevas en la terminal."""
    if not new_tenders:
        console.print("\n[dim]No hay licitaciones nuevas.[/dim]")
        return

    console.print(f"\n[bold green]{len(new_tenders)} licitaciones nuevas[/bold green] ({len(new_relevant)} relevantes)")

    if not new_relevant:
        return

    table = Table(title="Licitaciones Nuevas Relevantes", show_lines=True)
    table.add_column("Relevancia", style="bold", width=10)
    table.add_column("Nombre", max_width=60)
    table.add_column("Institución", max_width=30)
    table.add_column("Concurso", max_width=28)
    table.add_column("Fecha límite", width=12)

    colors = {"alta": "red", "media": "yellow", "baja": "blue"}

    for tender, classification in new_relevant[:30]:
        color = colors.get(classification.level, "white")
        table.add_row(
            f"[{color}]{classification.level}[/{color}]",
            tender.name[:60],
            tender.institution_name[:30],
            tender.inst_cartel_no,
            tender.bid_end_date or "—",
        )

    console.print(table)

    if len(new_relevant) > 30:
        console.print(f"[dim]...y {len(new_relevant) - 30} más. Revisa el dashboard.[/dim]")


def _send_notifications(notif_cfg: dict, tenders: list[tuple[Tender, Classification]]) -> None:
    """Envía notificaciones según configuración."""
    slack_cfg = notif_cfg.get("slack", {})
    if slack_cfg.get("enabled") and slack_cfg.get("webhook_url"):
        try:
            send_slack(slack_cfg["webhook_url"], tenders)
            console.print("[green]Notificación Slack enviada.[/green]")
        except Exception as e:
            console.print(f"[red]Error enviando a Slack: {e}[/red]")

    discord_cfg = notif_cfg.get("discord", {})
    if discord_cfg.get("enabled") and discord_cfg.get("webhook_url"):
        try:
            send_discord(discord_cfg["webhook_url"], tenders)
            console.print("[green]Notificación Discord enviada.[/green]")
        except Exception as e:
            console.print(f"[red]Error enviando a Discord: {e}[/red]")


@cli.command()
@click.pass_context
def dashboard(ctx: click.Context) -> None:
    """Regenera el dashboard HTML sin consultar SICOP."""
    cfg = ctx.obj["config"]
    db_path = BASE_DIR / cfg.get("database", "data/licitaciones.db")
    dashboard_path = BASE_DIR / cfg.get("dashboard_output", "data/dashboard.html")

    with Storage(db_path) as storage:
        path = generate_dashboard(storage, dashboard_path)
        console.print(f"[green]Dashboard generado:[/green] {path}")


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Muestra estadísticas de la base de datos."""
    cfg = ctx.obj["config"]
    db_path = BASE_DIR / cfg.get("database", "data/licitaciones.db")

    with Storage(db_path) as storage:
        s = storage.get_stats()

    console.print(f"\n[bold]Total licitaciones:[/bold] {s['total']}")
    console.print("\n[bold]Por relevancia:[/bold]")
    for level, count in sorted(s["by_relevance"].items()):
        console.print(f"  {level}: {count}")
    console.print("\n[bold]Top instituciones:[/bold]")
    for name, count in list(s["by_institution"].items())[:10]:
        console.print(f"  {name}: {count}")


if __name__ == "__main__":
    cli()
