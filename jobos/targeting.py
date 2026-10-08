"""Targeting: what the user WANTS (screening decides what they QUALIFY for).

Lives in config/settings.json under "targets". Nothing is hardcoded: no built-in city
list, no built-in role list. Example:

    "targets": {
      "roles": ["test engineer", "validation", "quality engineer", "firmware", "embedded", "ai engineer"],
      "exclude_titles": ["sales", "recruiter", "technician", "mechanical"],
      "locations": ["Austin, TX", "Tampa, FL"],
      "remote": true,
      "countries": ["United States", "Japan"],
      "home_country": "United States",
      "languages": ["English"]
    }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import paths

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}
_US_HINT = re.compile(r"(?i)\b(united states|usa|u\.s\.|us\b|" + "|".join(US_STATES.values()) + r")\b|,\s*(" +
                      "|".join(US_STATES) + r")\b")
REMOTE = re.compile(r"(?i)\b(remote|work from home|anywhere|distributed)\b")
OTHER_LANGUAGE = re.compile(
    r"(?i)\b(?:fluen(?:t|cy)|proficien(?:t|cy)|native|business[- ]level|bilingual|speak|written and spoken)\b"
    r"[^.\n]{0,40}\b(japanese|mandarin|chinese|korean|german|french|spanish|portuguese|italian|dutch|"
    r"hebrew|arabic|hindi|vietnamese|polish|russian|turkish)\b"
    r"|\b(japanese|mandarin|chinese|korean|german|french|spanish|portuguese)\b[^.\n]{0,25}\b(required|"
    r"fluency|fluent|proficiency|is a must)\b|\bJLPT\s*N?[1-3]\b|\bHSK\b|\bTOPIK\b")
VISA_SUPPORT = re.compile(r"(?i)\b(visa sponsorship|sponsor (?:a |your )?(?:work )?visa|relocation (?:package|support|assistance)|"
                          r"we (?:will|can) sponsor|visa support)\b")


@dataclass
class Targets:
    roles: list[str] = field(default_factory=list)
    exclude_titles: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    remote: bool = True
    countries: list[str] = field(default_factory=lambda: ["United States"])
    home_country: str = "United States"
    languages: list[str] = field(default_factory=lambda: ["English"])
    radius_miles: float | None = None        # with center: keep jobs within this many miles
    center: list[float] | None = None        # [lat, lon], e.g. [27.976, -82.503]

    @classmethod
    def load(cls) -> "Targets":
        t = paths.settings("targets")
        return cls(**{k: v for k, v in t.items() if k in cls.__dataclass_fields__})


@dataclass
class Match:
    ok: bool
    why: list[str] = field(default_factory=list)


def _words(s: str) -> str:
    return " " + re.sub(r"[^a-z0-9+#]+", " ", s.lower()) + " "


def title_ok(title: str, t: Targets) -> Match:
    tw = _words(title)
    for x in t.exclude_titles:
        if _words(x) in tw:
            return Match(False, [f"title contains excluded '{x}'"])
    if not t.roles:
        return Match(True)
    hit = next((r for r in t.roles if _words(r) in tw), None)
    return Match(bool(hit), [f"role match '{hit}'"] if hit else ["title matches none of your target roles"])


def _is_us(loc: str) -> bool:
    return bool(_US_HINT.search(loc))


def location_ok(location: str, t: Targets) -> Match:
    loc = location or ""
    if not loc.strip():
        return Match(True, ["no location listed"])
    if t.remote and REMOTE.search(loc):
        return Match(True, ["remote"])
    if t.radius_miles and t.center:
        from .geo import geocode, haversine_miles, segments
        found = False
        for seg in segments(loc):
            p = geocode(seg)
            if p is None:
                continue
            found = True
            d = haversine_miles((t.center[0], t.center[1]), p)
            if d <= t.radius_miles:
                return Match(True, [f"{seg} is {d:.1f} mi away"])
        if found and not t.locations:
            return Match(False, [f"location {loc!r} is more than {t.radius_miles:g} mi away"])
    low = loc.lower()
    for want in t.locations:
        city = want.split(",")[0].strip().lower()
        if city and city in low:
            return Match(True, [f"in {want}"])
    if not t.locations:                                   # no city list: filter by country only
        if _is_us(loc) and "United States" in t.countries:
            return Match(True, ["United States"])
        for c in t.countries:
            if c.lower() in low:
                return Match(True, [c])
    else:
        for c in t.countries:                             # whole foreign countries the user opted into
            if c != t.home_country and c.lower() in low:
                return Match(True, [c])
    return Match(False, [f"location {loc!r} is outside your targets"])


def text_ok(text: str, location: str, t: Targets) -> Match:
    """Checks that need the full description: language requirements and, abroad, visa support."""
    why = []
    m = OTHER_LANGUAGE.search(text or "")
    if m:
        lang = next(g for g in m.groups() if g) if any(m.groups()) else m.group(0)
        if not any(lang.lower().startswith(l.lower()[:4]) for l in t.languages):
            return Match(False, [f"requires {lang.strip()}"])
    abroad = location and not _is_us(location) and not REMOTE.search(location) and t.home_country == "United States"
    if abroad and not VISA_SUPPORT.search(text or ""):
        why.append("role is abroad and the posting doesn't mention visa sponsorship / relocation support")
    return Match(True, why)
