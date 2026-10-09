"""Fit score, 1.0 to 5.0, with the reasons behind it. Rule-based: no AI, same answer every time.

The screener decides "can I get this job at all"; the score ranks the jobs that pass, so the
top 3-5 really are the best. Below `min_score` (settings "profile", default 3.5) a job is called
a weak fit and left out of searches; you can still look at it with `scout --all`.

    role        0.35  your target role is in the title (whole phrase vs. some words)
    experience  0.35  required years vs. your limit, plus new-grad / entry-level wording
    location    0.15  your city or radius, remote, or just the right country
    flags       0.15  things to double-check (clearance to obtain, graduation window, ...)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .screen import Profile, Verdict
from .targeting import Targets, location_ok

WEIGHTS = {"role": 0.35, "experience": 0.35, "location": 0.15, "flags": 0.15}
NOT_A_FLAG = "no description fetched"          # title-only mode: unknown, not a warning
_GENERIC = {"engineer", "engineering", "analyst", "specialist", "associate", "developer", "i", "ii",
            "and", "of", "the", "a", "junior", "senior", "entry", "level"}


@dataclass
class Score:
    total: float
    parts: dict[str, int] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def label(self) -> str:
        return f"{self.total:.1f}/5"


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9+#]+", s.lower())


def _role(title: str, t: Targets) -> tuple[int, str]:
    if not t.roles:
        return 3, "no target roles set"
    tw = " " + " ".join(_words(title)) + " "
    for r in t.roles:
        if " " + " ".join(_words(r)) + " " in tw:
            return 5, f"title matches '{r}'"
    have = set(_words(title))
    for r in t.roles:
        shared = (set(_words(r)) - _GENERIC) & have
        if shared:
            return 3, f"title shares '{' '.join(sorted(shared))}' with '{r}'"
    return 1, "title matches none of your roles"


def _experience(v: Verdict, p: Profile) -> tuple[int, str]:
    if v.required_years is None:
        s, why = 4, "no years requirement found"
    else:
        gap = p.max_years - v.required_years
        s = 5 if gap >= 2 else 4 if gap == 1 else 3 if gap == 0 else 1
        why = f"asks {v.required_years}+ yrs (your limit {p.max_years})"
    if v.signals:
        s, why = min(5, s + 1), why + "; says " + ", ".join(f"'{x}'" for x in v.signals[:2])
    return s, why


def _location(location: str, t: Targets) -> tuple[int, str]:
    m = location_ok(location, t)
    why = m.why[0] if m.why else ""
    if not m.ok:
        return 1, why
    if why.startswith(("remote", "in ")):
        return 5, why
    d = re.match(r".* is ([\d.]+) mi away", why)
    if d and t.radius_miles:
        return (5 if float(d.group(1)) <= t.radius_miles / 2 else 4), why
    return 3, why or "location not listed"


def score(posting, v: Verdict, p: Profile, t: Targets, extra_flags: list[str] | None = None) -> Score:
    if not v.ok:
        return Score(1.0, {}, ["fails screening: " + "; ".join(v.reasons[:2])])
    flags = [f for f in v.flags + (extra_flags or []) if not f.startswith(NOT_A_FLAG)]
    parts, reasons = {}, []
    for name, (s, why) in (("role", _role(posting.title, t)), ("experience", _experience(v, p)),
                           ("location", _location(posting.location, t))):
        parts[name] = s
        reasons.append(f"{name} {s}/5: {why}")
    parts["flags"] = max(2, 5 - len(flags))
    reasons.append(f"flags {parts['flags']}/5: " + ("; ".join(flags) if flags else "none"))
    total = round(sum(WEIGHTS[k] * parts[k] for k in WEIGHTS), 1)
    return Score(total, parts, reasons)
