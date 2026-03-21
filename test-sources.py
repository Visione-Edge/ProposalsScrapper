"""Test que verifica cada fuente de licitaciones."""
import sys
sys.path.insert(0, ".")

from sources import get_enabled_sources
from sicop.scanner import load_config
from pathlib import Path

cfg = load_config(Path("."))
sources = get_enabled_sources(cfg)
print(f"Fuentes habilitadas: {len(sources)}")
for name, client in sources:
    print(f"\n  - {name}")
    try:
        tenders = client.fetch_recent_tenders(days_back=30)
        print(f"    OK: {len(tenders)} licitaciones")
        for t in tenders[:3]:
            print(f"      [{t.source}] {t.name[:80]}")
            print(f"        bid_end: {t.bid_end_date}  |  url: {t.source_url[:60]}")
    except Exception as e:
        print(f"    ERROR: {e}")
    finally:
        client.close()
