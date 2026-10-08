"""Where user data lives. Defaults to ./data next to the current directory;
override with the JOBOS_HOME environment variable. Everything here is gitignored."""
import os
from pathlib import Path


def home() -> Path:
    root = Path(os.environ.get("JOBOS_HOME") or Path.cwd() / "data")
    root.mkdir(parents=True, exist_ok=True)
    return root


def tracker_csv() -> Path:
    return home() / "tracker.csv"


def queue_csv() -> Path:
    return home() / "queue.csv"


def settings_json() -> Path:
    return Path(os.environ.get("JOBOS_CONFIG") or Path.cwd() / "config") / "settings.json"


def settings(section: str) -> dict:
    """One section ("rules", "profile", "targets") of settings.json, or {} if unset."""
    import json
    p = settings_json()
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get(section, {})
