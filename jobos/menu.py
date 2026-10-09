"""`firstrole` with no arguments: a numbered menu, for people who don't live in a terminal."""
from __future__ import annotations

import webbrowser
from datetime import date, timedelta
from typing import Callable

from . import dashboard, paths, search, tracker, wizard
from .screen import Profile
from .targeting import Targets

Ask = Callable[[str], str]
UPDATES = [("Applied", "I applied"), ("Interviewing", "I got an interview"), ("Offer", "I got an offer"),
           ("Rejected", "They said no"), ("Skipped", "Not interested")]
OPEN = {"Found", "Queued", "Applied", "Assessment", "Interviewing"}


def open_dashboard(say: Callable[[str], None] = print, launch: bool = True) -> None:
    out = dashboard.write(tracker.load(), paths.home() / "dashboard.html")
    say(f"Your jobs page: {out}")
    if launch:
        webbrowser.open(out.resolve().as_uri())


def update_job(ask: Ask, say: Callable[[str], None]) -> None:
    rows = tracker.load()
    live = [r for r in rows if r["status"].split(" - ")[0] in OPEN][-30:]
    if not live:
        say("No open jobs yet. Choose 'Find new jobs' first.")
        return
    for i, r in enumerate(live, 1):
        say(f"  {i:2}. [{r['status']}] {r['company']} | {r['title']}")
    pick = ask("Which job? (number, or Enter to go back): ").strip()
    if not pick.isdigit() or not 1 <= int(pick) <= len(live):
        return
    job = live[int(pick) - 1]
    for i, (_, label) in enumerate(UPDATES, 1):
        say(f"  {i}. {label}")
    choice = ask("What happened? (number): ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(UPDATES):
        return
    status = UPDATES[int(choice) - 1][0]
    today = date.today()
    extra = {"applied": today.isoformat(), "follow_up": (today + timedelta(days=14)).isoformat()} \
        if status == "Applied" else {}
    tracker.update(rows, job["id"], status=status, **extra)
    tracker.save(rows)
    say(f"Saved: {job['company']} -> {status}" + (" (follow up in 2 weeks)" if extra else ""))


def run(ask: Ask = input, say: Callable[[str], None] = print, launch: bool = True) -> int:
    try:
        if not paths.settings_json().exists():
            say("Welcome! A few questions first, so I know what to look for.\n")
            wizard.run(ask, say)
        while True:
            say("\nWhat would you like to do?\n"
                "  1. Find new jobs for me\n"
                "  2. See my jobs (opens in your browser)\n"
                "  3. Update a job (applied, interview, rejected...)\n"
                "  4. Change what I'm looking for\n"
                "  5. Quit")
            c = ask("Type a number and press Enter: ").strip()
            if c == "1":
                say("Searching (a minute or two; it goes slowly on purpose so LinkedIn doesn't block you)...")
                try:
                    added = search.run(Targets.load(), Profile.load(), say)
                except (ValueError, OSError) as e:          # no roles set, no internet, ...
                    say(f"Couldn't search: {e}")
                    continue
                say(f"\nAdded {len(added)} new job(s) to your list.")
                if added:
                    open_dashboard(say, launch)
            elif c == "2":
                open_dashboard(say, launch)
            elif c == "3":
                update_job(ask, say)
            elif c == "4":
                wizard.run(ask, say)
            elif c in ("5", "q", "quit", "exit"):
                return 0
    except (KeyboardInterrupt, EOFError):
        say("\nBye!")
        return 0
