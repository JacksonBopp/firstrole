"""Guardrails enforced in code, not just written in instructions.

An agent can ignore a sentence in a prompt; it cannot ignore `check()` raising before a
job enters the queue. Defaults are conservative and live in config/settings.json:

    {"rules": {"max_per_company": 3, "one_per_company_per_day": true,
               "skip_if_interviewing": true, "skip_companies": ["Example Corp"]}}
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date

from . import paths

DEFAULTS = {"max_per_company": 3, "one_per_company_per_day": True,
            "skip_if_interviewing": True, "skip_companies": []}


@dataclass
class Rules:
    max_per_company: int = 3
    one_per_company_per_day: bool = True
    skip_if_interviewing: bool = True
    skip_companies: list[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Rules":
        p = paths.settings_json()
        cfg = dict(DEFAULTS)
        if p.exists():
            cfg.update(json.loads(p.read_text(encoding="utf-8")).get("rules", {}))
        return cls(**{k: cfg[k] for k in DEFAULTS})


class RuleViolation(Exception):
    pass


def _same_company(a: str, b: str) -> bool:
    a, b = a.strip().lower(), b.strip().lower()
    return a == b or (len(a) > 3 and len(b) > 3 and (a in b or b in a))


def check(company: str, rows: list[dict], rules: Rules | None = None, today: str | None = None) -> None:
    """Raise RuleViolation if applying to `company` now would break a rule."""
    rules = rules or Rules.load()
    today = today or date.today().isoformat()
    mine = [r for r in rows if _same_company(r["company"], company)]
    if any(_same_company(s, company) for s in rules.skip_companies):
        raise RuleViolation(f"{company} is on your skip list")
    if rules.skip_if_interviewing and any(r["status"].startswith(("Interviewing", "Assessment", "Offer")) for r in mine):
        raise RuleViolation(f"You're already interviewing with {company}; don't dilute that with another application")
    applied = [r for r in mine if r["date_applied"]]
    if len(applied) >= rules.max_per_company:
        raise RuleViolation(f"Already {len(applied)} applications at {company} (limit {rules.max_per_company})")
    if rules.one_per_company_per_day and any(r["date_applied"] == today for r in applied):
        raise RuleViolation(f"Already applied to {company} today; one per company per day")
