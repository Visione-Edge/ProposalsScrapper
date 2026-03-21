# ProposalsScrapper — Progress Log

## 2026-03-21 | Multi-Source Procurement Scraping Architecture

### Docker / Infrastructure Fixed
- Fixed nginx SSL certificate issue for local development (certs didn't exist locally)
- Created `docker-compose.override.yml` for local dev (HTTP-only nginx, no certbot)
- Created `.dockerignore` to fix permission denied errors with certbot's root-owned files during build
- Created `init-local-certs.sh` for self-signed certs locally
- Fixed nginx "host not found in upstream" error

### Multi-Source Architecture
- Designed and implemented a multi-source architecture following `procurement_sources.md`
- Created `sources/` directory with one subfolder per source, each with `client.py`
- Created `sources/base.py` with `BaseTender` dataclass and `SourceClient` protocol
- Created `sources/__init__.py` as source registry with `get_enabled_sources(config)`
- Kept existing `sicop/` folder for scanner, storage, classifier, notifier (additive, not replaced)
- Added `source` and `source_url` columns to SQLite DB with auto-migration

### Source Clients (11 total)

| Source | File | Status | Results |
|--------|------|--------|---------|
| SICOP | `sources/sicop/client.py` | Working | 362 fetched, ~25 stored |
| World Bank | `sources/worldbank/client.py` | Working | 902 fetched, 197 new, 91 relevant |
| UNDP | `sources/undp/client.py` | Working | 105 fetched, 6 stored |
| IDB/BID | `sources/idb/client.py` | 0 results | CKAN CSV, no recent data |
| BCIE | `sources/bcie/client.py` | Working | 16 fetched, 1 stored |
| CAF | `sources/caf/client.py` | Working | 2 fetched, 1 stored |
| EU TED | `sources/eu_ted/client.py` | 0 results | Auth issues suspected |
| CCSS | `sources/ccss/client.py` | 0 results | No accessible data found |
| ICE/PEL | `sources/ice_pel/client.py` | Disabled | Requires login |
| UNGM | `sources/ungm/client.py` | Disabled | Requires headless browser |
| UNOPS | `sources/unops/client.py` | 0 relevant | 24 fetched, keyword mismatch |

### Scanner Updates
- Modified `sicop/scanner.py` to iterate over all enabled sources with error isolation
- Added per-source `days_back` configuration
- Added `_is_expired()` filter (bid_end_date passed OR registration_date > 6 months without deadline)
- Added detailed per-source logging: expired count, irrelevant count, new count
- Added `data/scan_progress.json` — real-time scan status via `/api/scan/status`

### Storage Updates
- `source` and `source_url` columns added with auto-migration + backfill for existing rows
- Auto-cleanup of expired tenders on startup (not favorites)
- `upsert_tender()` accepts `BaseTender` with source fields
- `get_stats()` returns `by_source` breakdown

### Keywords
- Added English translations for all Spanish keywords (alta/media/baja tiers)
- Added new English-only keywords: blockchain, IoT, RPA, NLP, computer vision, cloud infrastructure, managed services, etc.

### Frontend
- Source filter dropdown on dashboard
- Source badges on table rows and mobile cards (colored per source)
- Modal shows "Fuente" field and "Enlace" to original source URL
- Modal conditionally shows SICOP-specific fields only for SICOP tenders
- `isExpired()` filter hides expired tenders client-side
- Cache-busting query params on JS includes

### Current State
- 230 tenders in DB from multiple sources
- 6 sources actively bringing data; 4 storing relevant tenders
- World Bank is the biggest contributor after SICOP

---

## Pending Issues

| # | Issue | Priority |
|---|-------|----------|
| 1 | Revert scan rate limit to 2/hour (`app/routes/scan.py`) before production | HIGH |
| 2 | Verify source filter dropdown after latest rebuild | HIGH |
| 3 | EU TED — fix auth or switch to open TED API v3 endpoint | MEDIUM |
| 4 | UNOPS — 24 fetched but 0 relevant, keywords don't match English vocabulary | MEDIUM |
| 5 | IDB/BID — find correct REST API endpoint or country filter for CKAN | MEDIUM |
| 6 | Add `data/scan_progress.json` to `.gitignore` | LOW |
| 7 | ICE/PEL — requires login, no solution yet | LOW |
| 8 | UNGM — requires Playwright/headless browser | LOW |
| 9 | False positives in keyword matching (e.g., "CRM" in vehicle insurance) | LOW |
