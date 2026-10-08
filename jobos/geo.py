"""Offline geocoding for US job locations, so targets can say "within 10 miles of here".

Data: jobos/geodata/places.csv.gz, trimmed from the US Census Gazetteer places file (public domain;
rebuild with jobos/geodata/build_places.py). Every incorporated place and census-designated place
in the US, keyed by (name, state), with its internal point. No network, no API key.
"""
from __future__ import annotations

import csv
import gzip
import math
import re
from functools import lru_cache
from importlib import resources

_ABBR_BY_STATE: dict[str, str] = {}      # filled from targeting.US_STATES on first use


def _abbr(state: str) -> str | None:
    if not _ABBR_BY_STATE:
        from .targeting import US_STATES
        _ABBR_BY_STATE.update({v.lower(): k for k, v in US_STATES.items()})
        _ABBR_BY_STATE.update({k.lower(): k for k in US_STATES})
    return _ABBR_BY_STATE.get(state.strip().lower())


def _norm(name: str) -> str:
    n = re.sub(r"\s+", " ", name.lower()).strip()
    n = re.sub(r"^(saint|st\.?) ", "st. ", n)         # Census: "St. Petersburg"
    return re.sub(r"^ft\.? ", "fort ", n)              # Census: "Fort Lauderdale"


@lru_cache(maxsize=1)
def _places() -> dict[tuple[str, str], tuple[float, float]]:
    data = resources.files("jobos") / "geodata" / "places.csv.gz"
    out: dict[tuple[str, str], tuple[float, float]] = {}
    with data.open("rb") as raw, gzip.open(raw, "rt", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.setdefault((_norm(row["name"]), row["state"]), (float(row["lat"]), float(row["lon"])))
    return out


def lookup(city: str, state: str) -> tuple[float, float] | None:
    """(lat, lon) for a US city, or None. state may be "FL" or "Florida"."""
    st = _abbr(state)
    if not st or not city.strip():
        return None
    p = _places()
    c = _norm(city)
    return p.get((c, st)) or p.get((f"urban {c}", st))       # "Urban Honolulu" is how Census names it


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def segments(location: str) -> list[str]:
    """Split a listing's location field into one place per segment.
    Greenhouse joins several with ';'; some boards use ' | ' or ' / '."""
    return [s.strip() for s in re.split(r";|\s\|\s|\s/\s", location or "") if s.strip()]


def geocode(segment: str) -> tuple[float, float] | None:
    """Geocode "City, ST", "City, State", or "City, State, United States". None if unknown."""
    parts = [p.strip() for p in segment.split(",") if p.strip()]
    parts = [p for p in parts if not re.fullmatch(r"(?i)united states( of america)?|usa|us", p)]
    if len(parts) < 2:
        return None
    city = re.sub(r"(?i)^(remote|hybrid|onsite|on-site)\s*[-:]\s*", "", parts[0])
    return lookup(city, parts[1])


def locate_home(text: str, online: bool = True) -> tuple[tuple[float, float] | None, str]:
    """A user's home point from what they type: "40.71, -74.00" (copied from a map), "Tampa, FL"
    (offline), or a street address (one OpenStreetMap lookup). Returns (point or None, how)."""
    m = re.fullmatch(r"\s*(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*", text)
    if m:
        return (float(m.group(1)), float(m.group(2))), "coordinates"
    p = geocode(text)
    if p:
        return p, "city center"
    if online:
        from .adapters.base import http_json
        try:
            hits = http_json("https://nominatim.openstreetmap.org/search",
                             params={"q": text, "format": "json", "limit": 1, "countrycodes": "us"})
        except Exception:
            hits = []
        if hits:
            return (float(hits[0]["lat"]), float(hits[0]["lon"])), "address"
    parts = [s.strip() for s in text.split(",")]          # "Some St & Other St, Tampa, FL" -> the city
    for i in range(len(parts) - 1):
        p = geocode(", ".join(parts[i:i + 2]))
        if p:
            return p, f"center of {parts[i]} (address not found)"
    return None, "not found"
