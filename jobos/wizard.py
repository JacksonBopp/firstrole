"""`jobos init`: a few plain questions that write config/settings.json.

Every answer has a default (press Enter), and running it again shows your current
answers as the defaults, so it doubles as "edit my settings".
"""
from __future__ import annotations

import json
import re
from typing import Callable

from . import geo, paths, titles
from .rules import DEFAULTS as RULE_DEFAULTS

Ask = Callable[[str], str]


def _list(s: str) -> list[str]:
    return [x.strip() for x in s.replace(";", ",").split(",") if x.strip()]


def _places(s: str) -> list[str]:
    """Locations are "City, ST" so commas belong to them; separate places with ';'."""
    return [x.strip() for x in s.split(";") if x.strip()]


def _yes(s: str) -> bool:
    return s.strip().lower() in {"y", "yes", "true", "1"}


def run(ask: Ask = input, say: Callable[[str], None] = print) -> dict:
    p = paths.settings_json()
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    prof, tgt, rul = cur.get("profile", {}), cur.get("targets", {}), {**RULE_DEFAULTS, **cur.get("rules", {})}

    def q(prompt: str, default) -> str:
        shown = "; ".join(default) if isinstance(default, list) else (
            ("y" if default else "n") if isinstance(default, bool) else str(default))
        ans = ask(f"{prompt} [{shown}]: ").strip()
        return ans if ans else shown

    say("Set up firstrole. Press Enter to keep the value in [brackets].\n")
    say("What jobs do you want? (comma-separated keywords matched against job titles)")
    roles = _list(q("  Target roles, e.g. test engineer, data analyst", tgt.get("roles", [])))
    ideas = titles.related(roles)
    if ideas:
        say("  Jobs like these often go by other names too:")
        for i, t in enumerate(ideas, 1):
            say(f"    {i}. {t}")
        pick = ask("  Add any? (numbers like 1,3, or Enter to skip): ").strip()
        roles += [ideas[int(n) - 1] for n in re.findall(r"\d+", pick) if 0 < int(n) <= len(ideas)]
    exclude = _list(q("  Skip titles containing", tgt.get("exclude_titles", ["sales", "recruiter"])))
    say("Where? (separate places with ';')")
    locations = _places(q("  Cities, e.g. Austin, TX; Tampa, FL  (blank = anywhere in your countries)",
                          tgt.get("locations", [])))
    radius = q("  Only jobs within how many miles of home? (blank = no limit)", tgt.get("radius_miles") or "")
    center = tgt.get("center")
    if radius:
        home = q("  Home: street address, 'City, ST', or 'lat, lon' copied from a map",
                 f"{center[0]}, {center[1]}" if center else "")
        point, how = geo.locate_home(home) if home else (None, "not given")
        if point:
            center = [round(point[0], 4), round(point[1], 4)]
            say(f"    -> {center[0]}, {center[1]} ({how})")
        else:
            say("    -> couldn't find that place; no distance limit set (try 'City, ST')")
            radius = ""
    remote = _yes(q("  Include remote jobs? (y/n)", tgt.get("remote", True)))
    countries = _list(q("  Countries", tgt.get("countries", ["United States"])))
    languages = _list(q("  Languages you work in", tgt.get("languages", ["English"])))
    say("About you (used only to skip jobs you can't get; never sent anywhere)")
    max_years = int(q("  Most years of experience a job may REQUIRE", prof.get("max_years", 2)))
    citizen = _yes(q("  US citizen? (y/n)", prof.get("us_citizen", False)))
    sponsor = _yes(q("  Need visa sponsorship? (y/n)", prof.get("needs_sponsorship", False)))
    interns = _yes(q("  Include internships / co-ops? (y/n)", prof.get("include_internships", False)))
    say("Pacing rules")
    cap = int(q("  Max applications per company", rul["max_per_company"]))

    cur["targets"] = {**tgt, "roles": roles, "exclude_titles": exclude, "locations": locations,
                      "radius_miles": float(radius) if radius else None, "center": center if radius else None,
                      "remote": remote, "countries": countries or ["United States"],
                      "languages": languages or ["English"]}
    cur["profile"] = {**prof, "max_years": max_years, "us_citizen": citizen,
                      "needs_sponsorship": sponsor, "include_internships": interns}
    cur["rules"] = {**rul, "max_per_company": cap}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
    say(f"\nSaved your answers ({p}). You can change them any time.")
    return cur
