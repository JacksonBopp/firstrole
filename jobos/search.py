"""`jobos search` / menu "Find new jobs": turn your settings into searches, so nobody has to paste URLs.

Your target roles x your places (plus remote) become LinkedIn logged-out searches. Results go through
the same filters as `scout --fetch`, and the fits are added to your tracker as "Found".
"""
from __future__ import annotations

import re
import urllib.error
from typing import Callable
from urllib.parse import urlencode

from . import geo, tracker
from .adapters import linkedin
from .adapters.base import Posting
from .screen import Profile, screen
from .targeting import Targets, location_ok, text_ok, title_ok

PAST_MONTH = "r2592000"
REMOTE_TAG = "(Remote per LinkedIn)"
NOT_REMOTE = re.compile(r"(?i)\b(hybrid (?:role|position|schedule|approach|work)|in-office|on-?site (?:role|position|presence)|"
                        r"days? (?:a|per) week in (?:the )?office|must reside)\b")
MAX_ROLES, MAX_PLACES, MAX_FETCH = 6, 3, 30


def plan(t: Targets) -> list[dict]:
    """The searches to run: one per (role, place), plus one remote search per role."""
    if not t.roles:
        raise ValueError("Tell me what jobs you want first (setup: 'jobos init').")
    places = t.locations[:MAX_PLACES]
    if not places and t.center:
        places = [geo.nearest((t.center[0], t.center[1]))]
    distance = str(int(t.radius_miles)) if t.radius_miles else "25"
    out = []
    for role in t.roles[:MAX_ROLES]:
        for place in places:
            out.append({"keywords": role, "location": place, "distance": distance, "f_TPR": PAST_MONTH})
        if t.remote or not places:
            q = {"keywords": role, "location": t.home_country or "United States", "f_TPR": PAST_MONTH}
            if places:
                q["f_WT"] = "2"                                  # remote only; local is covered above
            out.append(q)
    return out


def run(t: Targets, prof: Profile, say: Callable[[str], None] = print) -> list[dict]:
    """Search, screen, and add the fits to the tracker. Returns the rows added."""
    queries = plan(t)
    pages = 2 if len(queries) <= 8 else 1                       # keep the total request count modest
    rows = tracker.load()
    tracked = {r["id"] for r in rows}
    seen: dict[str, Posting] = {}
    for q in queries:
        where = q["location"] + (" (remote)" if q.get("f_WT") else "")
        try:
            found = linkedin.list_postings("https://www.linkedin.com/jobs/search/?" + urlencode(q), pages=pages)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                say("  LinkedIn asked us to slow down. Showing what we have; try again in an hour.")
                break
            raise
        new = [p for p in found if p.url not in seen and tracker.job_id(p.url) not in tracked]
        for p in new:
            if q.get("f_WT") and "remote" not in p.location.lower():
                p.location = f"{p.location} {REMOTE_TAG}".strip()  # LinkedIn's remote filter; not always right
            seen[p.url] = p
        say(f"  {q['keywords']} near {where}: {len(found)} listed, {len(new)} new")
    wanted = [p for p in seen.values()
              if title_ok(p.title, t).ok and location_ok(p.location, t).ok]
    say(f"Reading {min(len(wanted), MAX_FETCH)} of {len(wanted)} promising postings in full...")
    added = []
    for p in wanted[:MAX_FETCH]:
        try:
            full = linkedin.fetch_posting(p.url)
        except urllib.error.HTTPError:
            break                                                 # rate limited: keep what we have
        except Exception:
            continue
        if p.location.endswith(REMOTE_TAG):
            full.location = p.location
        v = screen(full, prof)
        m = text_ok(full.text, full.location, t)
        if not (v.ok and m.ok):
            continue
        if full.location.endswith(REMOTE_TAG) and NOT_REMOTE.search(full.text):
            v.flags.append("listed as remote, but the posting mentions hybrid / in-office work: check")
        notes = "; ".join(v.flags + m.why) or "looks like a fit"
        added.append(tracker.add(rows, company=full.company, title=full.title, url=full.url,
                                 location=full.location, category="search", note=f"found by search: {notes}"))
        say(f"  FIT  {full.company} | {full.title} | {full.location}")
    tracker.save(rows)
    return added
