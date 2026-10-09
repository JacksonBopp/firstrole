"""`jobos` command line. Same commands on Windows, macOS and Linux.

    jobos init                                # guided setup -> config/settings.json
    jobos find <text>
    jobos add --company C --title T --url U [--status Found] [--resume R] [--note N]
    jobos update <id|url> [--status S] [--applied YYYY-MM-DD] [--follow-up D] [--resume R] [--note N]
    jobos summary
    jobos export <file.xlsx>
    jobos check <company>                     # would applying now break a rule?
    jobos screen <posting-url> [--max-years 2] [--citizen] [--internships]
    jobos scout <board-url> [--search text] [--max-years 2] [--citizen] [--fetch]
    jobos queue add --company C --title T --url U [--priority 1-5] [--resume R] [--by agent]
    jobos queue list [status]
    jobos queue next [--claim agent]
    jobos queue done|block|skip <id> [--note N]
    jobos queue release <id>
    jobos queue stale [--hours 3]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import queue as q
from . import rules, tracker


def _fmt(r: dict) -> str:
    return f"[{r['id']}] [{r['status']}] {r['company']} | {r['title']} | {r.get('location', '')}\n      {r['url']}"


def _qfmt(r: dict) -> str:
    return f"#{r['id']} [{r['status']}] P{r['priority']} {r['company']} | {r['title']}  (by {r['added_by']})\n      {r['url']}"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles
    if not (sys.argv[1:] if argv is None else argv):
        from . import menu                         # plain `jobos`: the friendly menu
        return menu.run()
    ap = argparse.ArgumentParser(prog="jobos", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="guided setup: what jobs you want and where")
    sub.add_parser("find").add_argument("text")
    a = sub.add_parser("add")
    for k in ("company", "title", "url"):
        a.add_argument(f"--{k}", required=True)
    for k in ("category", "location", "resume", "applied", "note"):
        a.add_argument(f"--{k}", default="")
    a.add_argument("--status", default="Found")
    u = sub.add_parser("update")
    u.add_argument("key")
    for k in ("status", "applied", "follow-up", "resume", "note"):
        u.add_argument(f"--{k}")
    sub.add_parser("summary")
    sub.add_parser("export").add_argument("out")
    sub.add_parser("dashboard", help="write a map + tracker page").add_argument("out", nargs="?", default="dashboard.html")
    sub.add_parser("search", help="search LinkedIn for your target roles/places; add fits to the tracker")
    sub.add_parser("check").add_argument("company")
    for name in ("screen", "scout"):
        sp = sub.add_parser(name)
        sp.add_argument("url")
        # Defaults come from config/settings.json ("profile"); these flags override it.
        sp.add_argument("--max-years", type=int, default=None)
        sp.add_argument("--citizen", action="store_true", default=None, help="you are a US citizen")
        sp.add_argument("--sponsorship", action="store_true", default=None, help="you need visa sponsorship")
        sp.add_argument("--internships", action="store_true", default=None, help="include internships / co-ops")
        if name == "scout":
            sp.add_argument("--search", default="")
            sp.add_argument("--fetch", action="store_true", help="fetch full text for each result (slower, more accurate)")
            sp.add_argument("--all", action="store_true", help="show skipped postings too")
            sp.add_argument("--any-role", action="store_true", help="ignore your target roles/locations")

    qp = sub.add_parser("queue").add_subparsers(dest="qcmd", required=True)
    qa = qp.add_parser("add")
    for k in ("company", "title", "url"):
        qa.add_argument(f"--{k}", required=True)
    qa.add_argument("--priority", type=int, default=3)
    for k in ("resume", "ats", "notes"):
        qa.add_argument(f"--{k}", default="")
    qa.add_argument("--by", default="human")
    qp.add_parser("list").add_argument("status", nargs="?")
    qp.add_parser("next").add_argument("--claim")
    for name in ("done", "block", "skip"):
        p = qp.add_parser(name)
        p.add_argument("qid")
        p.add_argument("--note", default="")
    qp.add_parser("release").add_argument("qid")
    qp.add_parser("stale").add_argument("--hours", type=float, default=3)

    args = ap.parse_args(argv)
    try:
        return _run(args)
    except (KeyError, ValueError, rules.RuleViolation) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 1


def _run(args) -> int:
    if args.cmd == "queue":
        return _run_queue(args)
    if args.cmd == "init":
        from . import wizard
        wizard.run()
        return 0
    rows = tracker.load()
    if args.cmd == "find":
        hits = tracker.find(rows, args.text)
        print("\n".join(_fmt(r) for r in hits) or "No matches.")
    elif args.cmd == "add":
        r = tracker.add(rows, company=args.company, title=args.title, url=args.url, status=args.status,
                        category=args.category, location=args.location, resume=args.resume,
                        applied=args.applied, note=args.note)
        tracker.save(rows)
        print("Added:\n" + _fmt(r))
    elif args.cmd == "update":
        r = tracker.update(rows, args.key, status=args.status, applied=args.applied,
                           follow_up=getattr(args, "follow_up"), resume=args.resume, note=args.note)
        tracker.save(rows)
        print("Updated:\n" + _fmt(r))
    elif args.cmd == "summary":
        for status, n in tracker.summary(rows):
            print(f"{n:5}  {status}")
    elif args.cmd == "export":
        print(f"Wrote {tracker.export_xlsx(rows, Path(args.out))} rows to {args.out}")
    elif args.cmd == "search":
        from . import search, screen, targeting
        added = search.run(targeting.Targets.load(), screen.Profile.load())
        print(f"\nAdded {len(added)} new job(s). See them: jobos dashboard")
    elif args.cmd == "dashboard":
        from . import dashboard
        print(f"Wrote {dashboard.write(rows, Path(args.out))}")
    elif args.cmd == "check":
        rules.check(args.company, rows)
        print(f"OK to apply to {args.company}")
    elif args.cmd in ("screen", "scout"):
        return _run_screen(args, rows)
    return 0


def _run_screen(args, rows) -> int:
    from . import adapters, screen, targeting
    prof = screen.Profile.load(max_years=args.max_years, us_citizen=args.citizen,
                               needs_sponsorship=args.sponsorship, include_internships=args.internships)
    tgt = targeting.Targets.load()
    tracked = {tracker.job_id(r["url"]) for r in rows}
    if args.cmd == "screen":
        p = adapters.fetch_posting(args.url)
        v = screen.screen(p, prof)
        v.flags += targeting.text_ok(p.text, p.location, tgt).why
        print(f"{p.title} | {p.location} | {p.source}\n  " + v.summary())
        if p.source == "linkedin" and p.is_open:
            home = adapters.linkedin.company_board(p.company, p.title)
            print(f"  Apply on the company site: {home}" if home else
                  f"  LinkedIn hides the apply link; find it on {p.company}'s careers page.")
        return 0
    try:
        found = adapters.list_postings(args.url, args.search)
    except adapters.NotFound:
        print(f"error: no job board found at {args.url} (check the company's board name)", file=sys.stderr)
        return 1
    shown = off_target = 0
    for p in found:
        # Cheap checks first: is this a job you WANT? Only then fetch and check if you QUALIFY.
        why_not = [] if args.any_role else [
            w for m in (targeting.title_ok(p.title, tgt), targeting.location_ok(p.location, tgt))
            if not m.ok for w in m.why]
        if why_not and not args.all:
            off_target += 1
            continue
        if args.fetch and not p.text and not why_not:
            try:
                p = adapters.fetch_posting(p.url)
            except Exception as e:                       # one bad posting shouldn't stop the scan
                print(f"  (could not fetch {p.url}: {e})")
                continue
        v = screen.screen(p, prof)
        if p.text:
            m = targeting.text_ok(p.text, p.location, tgt)
            (v.flags if m.ok else why_not).extend(m.why)
        ok = v.ok and not why_not
        if ok or args.all:
            mark = " [tracked]" if tracker.job_id(p.url) in tracked else ""
            print(f"{'FIT ' if ok else 'SKIP'} {p.company} | {p.title} | {p.location}{mark}\n     {p.url}")
            for line in (why_not + v.reasons + v.flags)[:3]:
                print(f"     - {line}")
            shown += 1
    tail = f", {off_target} outside your target roles/locations" if off_target else ""
    print(f"\n{shown} of {len(found)} shown{tail}" + ("" if args.fetch else "  (titles only; add --fetch to screen full text)"))
    return 0


def _run_queue(args) -> int:
    c = args.qcmd
    if c == "add":
        r = q.add(company=args.company, title=args.title, url=args.url, resume=args.resume, priority=args.priority,
                  ats=args.ats, notes=args.notes, by=args.by)
        print("Queued:\n" + _qfmt(r))
    elif c == "list":
        want = {args.status} if args.status else {"queued", "in_progress", "blocked"}
        rows = [r for r in q.load() if r["status"] in want]
        print("\n".join(_qfmt(r) for r in rows) or "Queue empty.")
    elif c == "next":
        r = q.next_job(args.claim)
        print(_qfmt(r) if r else "NONE")
    elif c in ("done", "block", "skip"):
        r = q.finish(args.qid, {"done": "applied", "block": "blocked", "skip": "skipped"}[c], args.note)
        print(_qfmt(r))
    elif c == "release":
        print(_qfmt(q.release(args.qid)))
    elif c == "stale":
        print(f"released {q.release_stale(args.hours)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
