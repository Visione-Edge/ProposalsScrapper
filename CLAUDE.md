# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SICOP Tender Monitor — a FastAPI web app that scrapes Costa Rica's SICOP procurement API, classifies tenders by relevance using a 3-tier keyword system (alta/media/baja), and presents them in a dashboard with favorites, notes, and notifications (Slack, Discord, email).

## Commands

```bash
# Run locally (dev)
uvicorn app.main:app --reload

# Run with Docker (production)
docker compose up -d

# First-time SSL setup on EC2
sudo bash init-letsencrypt.sh

# Local dev with self-signed certs (so nginx SSL config works)
bash init-local-certs.sh

# CLI commands
python main.py scan                 # One-off scan with notifications
python main.py scan --days 7        # Scan last 7 days
python main.py scan --no-notify     # Scan without notifications
python main.py dashboard            # Regenerate static HTML dashboard
python main.py stats                # Print DB statistics
```

## Architecture

Two entry points into the same `sicop/` core:

- **Web app** (`app/`): FastAPI with Jinja2 templates, serves dashboard at `/`, triggers scans via `/api/scan`
- **CLI** (`main.py`): Click commands for one-off scans and dashboard generation

### Core pipeline (`sicop/`)

`scanner.py` orchestrates: `client.py` (fetch from SICOP API) → `classifier.py` (keyword matching) → `storage.py` (SQLite upsert) → `notifier.py` (Slack/Discord/email)

### Web app (`app/`)

- `main.py` — App setup, lifespan (scheduler start/stop), auth middleware, CSRF middleware
- `auth.py` — Cookie-based sessions (in-memory OrderedDict), bcrypt auth, CSRF tokens (HMAC-signed), brute-force lockout (15 attempts/15 min per IP)
- `state.py` — Global singletons: config, rate limiter, scan state dict
- `scheduler.py` — APScheduler cron job for daily scans (timezone: America/Costa_Rica)
- `routes/` — auth, tenders (dashboard + CRUD APIs), scan (trigger + status polling), settings (keyword editor)

### Key design decisions

- **Dual PK**: Tenders identified by `(cartel_no, cartel_seq)` — both needed for uniqueness
- **Sessions are in-memory**: No Redis; sessions lost on restart; max 5 concurrent (FIFO eviction)
- **CSRF has two paths**: HTML forms use hidden token fields; API calls require `X-Requested-With: XMLHttpRequest` header
- **Rate limiting**: `/login` = 5/min, `/api/scan` = 2/hour (via slowapi, trusts X-Real-IP)
- **Keywords editable at runtime**: `/settings` writes directly to `keywords.yaml`

## Configuration

- `config.yaml` — scan schedule, API pagination, notification settings, procedure/institution filters
- `keywords.yaml` — 3-tier keyword lists (alta/media/baja) with word-boundary regex matching
- `.env` — SECRET_KEY, SICOP_USERNAME, SICOP_PASSWORD_HASH, SECURE_COOKIES, MAX_SESSIONS

Set `SECURE_COOKIES=false` in `.env` for local dev without HTTPS.

## Docker setup

3 services: `web` (FastAPI on :8000), `nginx` (reverse proxy :80/:443), `certbot` (Let's Encrypt renewal). The `nginx.conf` expects SSL certs to exist — use `init-letsencrypt.sh` on EC2 or `init-local-certs.sh` for local dev.

The `.dockerignore` excludes `data/` to avoid permission issues with certbot's root-owned files during build context.

## Domain terminology

- **Licitación** = tender/procurement opportunity
- **Cartel** = tender posting (cartel_no = number, cartel_seq = sequence)
- **Adjudicado** = awarded; **Contratado** = contracted
- **Relevance tiers**: alta (high, software/AI), media (medium, IT infra), baja (low, hardware/licenses)
