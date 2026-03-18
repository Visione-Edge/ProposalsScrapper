"""Shared application state and configuration helpers."""

from ipaddress import ip_address, ip_network
from pathlib import Path

import yaml
from fastapi import Request
from fastapi.templating import Jinja2Templates
from slowapi import Limiter

from sicop.storage import Storage

BASE_DIR = Path(__file__).parent.parent

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

scan_state: dict = {
    "running": False,
    "error": None,
    "last_result": None,
    "log": [],
}

_TRUSTED_PROXIES = [
    ip_network("172.16.0.0/12"),
    ip_network("10.0.0.0/8"),
    ip_network("127.0.0.0/8"),
    ip_network("192.168.0.0/16"),
]


def get_real_ip(request: Request) -> str:
    """Extract client IP, only trusting X-Real-IP from known proxies."""
    client_ip = request.client.host if request.client else "unknown"
    if client_ip != "unknown":
        try:
            addr = ip_address(client_ip)
            if any(addr in net for net in _TRUSTED_PROXIES):
                forwarded = request.headers.get("X-Real-IP")
                if forwarded:
                    return forwarded
        except ValueError:
            pass
    return client_ip


limiter = Limiter(key_func=get_real_ip)


def get_config() -> dict:
    config_path = BASE_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_storage() -> Storage:
    config = get_config()
    db_path = BASE_DIR / config.get("database", "data/licitaciones.db")
    return Storage(db_path)
