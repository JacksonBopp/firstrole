"""Where user data lives. Everything here stays on your machine.

- Inside a checkout of this repo (./data or ./config exists): ./data and ./config, as before.
- Anywhere else (e.g. started from the desktop shortcut): ~/job-search-os/data and ~/job-search-os/config.
- JOBOS_HOME / JOBOS_CONFIG override either.
"""
import os
from pathlib import Path


def base() -> Path:
    cwd = Path.cwd()
    if (cwd / "data").is_dir() or (cwd / "config").is_dir():
        return cwd
    return Path.home() / "job-search-os"


def home() -> Path:
    root = Path(os.environ.get("JOBOS_HOME") or base() / "data")
    root.mkdir(parents=True, exist_ok=True)
    return root


def tracker_csv() -> Path:
    return home() / "tracker.csv"


def queue_csv() -> Path:
    return home() / "queue.csv"


def settings_json() -> Path:
    return Path(os.environ.get("JOBOS_CONFIG") or base() / "config") / "settings.json"


def settings(section: str) -> dict:
    """One section ("rules", "profile", "targets") of settings.json, or {} if unset."""
    import json
    p = settings_json()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get(section, {})
