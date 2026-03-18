"""Generador de dashboard HTML interactivo."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from .storage import Storage

TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "dashboard.html"


def generate_dashboard(storage: Storage, output_path: str | Path) -> Path:
    """Genera el dashboard HTML con los datos actuales."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    tenders = storage.get_all_tenders()
    stats = storage.get_stats()

    # Parsear matched_keywords de JSON string a lista
    for t in tenders:
        if isinstance(t.get("matched_keywords"), str):
            t["matched_keywords"] = json.loads(t["matched_keywords"])

    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    html = template.render(
        tenders=tenders,
        tenders_json=json.dumps(tenders, ensure_ascii=False, default=str),
        stats=stats,
    )
    output.write_text(html, encoding="utf-8")
    return output.resolve()
