"""A work queue that several agents can share (e.g. Claude on a desktop, Codex on a laptop).

Lifecycle: queued -> in_progress (claimed) -> applied | blocked | skipped
  blocked = needs the human (password, phone code, CAPTCHA, a question only they can answer)
  skipped = closed, or not a fit once the full posting was read

`add` runs the rule checks first, and `done` updates the tracker in the same step, so the
two files can't drift apart.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

from . import paths, rules, tracker

COLUMNS = ["id", "added", "added_by", "priority", "company", "title", "url", "resume", "ats",
           "notes", "status", "claimed_by", "claimed_at", "result"]


def load(path: Path | None = None) -> list[dict]:
    path = path or paths.queue_csv()
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict], path: Path | None = None) -> None:
    path = path or paths.queue_csv()
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def _find(q: list[dict], qid: str) -> dict:
    for r in q:
        if r["id"] == str(qid):
            return r
    raise KeyError(f"No queue item #{qid}")


def add(*, company: str, title: str, url: str, resume: str = "", priority: int = 3, ats: str = "",
        notes: str = "", by: str = "human", check_rules: bool = True) -> dict:
    q, t = load(), tracker.load()
    if any(tracker.normalize_url(r["url"]) == tracker.normalize_url(url) for r in q):
        raise ValueError("Already in the queue")
    if check_rules:
        rules.check(company, t)
    nid = str(max([int(r["id"]) for r in q] or [0]) + 1)
    row = dict(id=nid, added=date.today().isoformat(), added_by=by, priority=str(priority), company=company,
               title=title, url=url, resume=resume, ats=ats, notes=notes, status="queued",
               claimed_by="", claimed_at="", result="")
    q.append(row)
    save(q)
    try:                                   # mirror into the tracker so it's never "queued but untracked"
        tracker.add(t, company=company, title=title, url=url, status="Queued", resume=resume, note=notes)
        tracker.save(t)
    except ValueError:
        pass
    return row


def next_job(claim_by: str | None = None) -> dict | None:
    q = load()
    waiting = sorted((r for r in q if r["status"] == "queued"), key=lambda r: (int(r["priority"] or 9), int(r["id"])))
    if not waiting:
        return None
    job = waiting[0]
    if claim_by:
        job.update(status="in_progress", claimed_by=claim_by, claimed_at=datetime.now().isoformat(timespec="minutes"))
        save(q)
    return job


def finish(qid: str, outcome: str, note: str = "") -> dict:
    """outcome: applied | blocked | skipped. 'applied' also marks the tracker row Applied."""
    if outcome not in {"applied", "blocked", "skipped"}:
        raise ValueError("outcome must be applied, blocked or skipped")
    q = load()
    job = _find(q, qid)
    job.update(status=outcome, result=f"{datetime.now().isoformat(timespec='minutes')}: {note}".strip())
    save(q)
    t = tracker.load()
    status = {"applied": "Applied", "blocked": "Blocked", "skipped": "Skipped"}[outcome]
    try:
        tracker.update(t, job["url"], status=status, note=note or None,
                       applied=date.today().isoformat() if outcome == "applied" else None,
                       follow_up=(date.today() + timedelta(days=14)).isoformat() if outcome == "applied" else None)
    except KeyError:
        tracker.add(t, company=job["company"], title=job["title"], url=job["url"], status=status,
                    resume=job["resume"], applied=date.today().isoformat() if outcome == "applied" else "", note=note)
    tracker.save(t)
    return job


def release(qid: str) -> dict:
    q = load()
    job = _find(q, qid)
    job.update(status="queued", claimed_by="", claimed_at="")
    save(q)
    return job


def release_stale(hours: float = 3) -> int:
    """Return jobs claimed by an agent that crashed or ran out of usage."""
    q = load()
    cutoff = datetime.now() - timedelta(hours=hours)
    n = 0
    for r in q:
        if r["status"] == "in_progress" and r["claimed_at"] and datetime.fromisoformat(r["claimed_at"]) < cutoff:
            r.update(status="queued", claimed_by="", claimed_at="")
            n += 1
    save(q)
    return n


def added_today(by: str | None = None) -> int:
    today = date.today().isoformat()
    return sum(1 for r in load() if r["added"] == today and (by is None or r["added_by"] == by))
