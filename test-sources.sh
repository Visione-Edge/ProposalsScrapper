#!/bin/bash
docker compose exec web python -c "
from sources import get_enabled_sources
from sicop.scanner import load_config
from pathlib import Path

cfg = load_config(Path('/app'))
sources = get_enabled_sources(cfg)
print('Fuentes habilitadas:')
for name, client in sources:
    print(f'  - {name}')
    try:
        tenders = client.fetch_recent_tenders(days_back=30)
        print(f'    OK: {len(tenders)} licitaciones')
        for t in tenders[:3]:
            print(f'      [{t.source}] {t.name[:80]}')
    except Exception as e:
        print(f'    ERROR: {e}')
    finally:
        client.close()
"
