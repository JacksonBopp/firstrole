# job-search-os

[![tests](https://github.com/JacksonBopp/job-search-os/actions/workflows/tests.yml/badge.svg)](https://github.com/JacksonBopp/job-search-os/actions/workflows/tests.yml)

Find jobs you actually qualify for, track every application, and let any AI agent help, on Windows, macOS, or Linux.

- **Reads the full posting, not just the title.** It tells "3+ years required" apart from "2-5 years preferred," catches clearance, citizenship, and degree requirements, and flags postings in another language.
- **Pulls from company job boards directly:** Greenhouse, Lever, Ashby, Workday, Oracle Cloud, SmartRecruiters, Workable, and Amazon, through their public APIs. Optional LinkedIn search reads its public logged-out pages, slowly. No login, no API keys.
- **One tracker, one source of truth.** A plain CSV that you can open in Excel, plus pacing rules (for example, at most 3 applications per company) that every agent has to follow.
- **Works with any AI tool, or none.** It's an ordinary command-line tool, so Claude Code, Codex, Cursor, Gemini, or a local model can run it, and so can you.

## Start here (no coding needed)

**1. Paste one line.**

- **Windows:** press Start, type `PowerShell`, press Enter, then paste this and press Enter:
  ```
  irm https://raw.githubusercontent.com/JacksonBopp/job-search-os/main/install.ps1 | iex
  ```
- **Mac:** press Cmd+Space, type `Terminal`, press Enter, then paste this and press Enter:
  ```
  curl -fsSL https://raw.githubusercontent.com/JacksonBopp/job-search-os/main/install.sh | sh
  ```
  (If it says Python is needed, install it from [python.org](https://www.python.org/downloads/) first.)

**2. Answer a few questions:** what jobs you want, where, and how much experience you have.

**3. Pick "Find new jobs for me".** It searches, reads every posting, and opens a page in your browser with the jobs that fit you, on a map.

Next time, just double-click **Job Search** on your desktop:

```
What would you like to do?
  1. Find new jobs for me
  2. See my jobs (opens in your browser)
  3. Update a job (applied, interview, rejected...)
  4. Change what I'm looking for
  5. Quit
```

> **Using the Claude or ChatGPT chat app?** It can't install this for you, because chat apps run in a sandbox, not on your computer. Paste the line above yourself; it takes about two minutes. (Claude Code, Codex, and Cursor *can* run it for you: see [Using it with an AI agent](#using-it-with-an-ai-agent).)

Your job list stays on your computer, in a `job-search-os` folder in your home folder. To update, paste the same line again.

## Quick start for developers

Needs Python 3.10+.

```bash
git clone https://github.com/JacksonBopp/job-search-os.git
cd job-search-os
python -m pip install -e .
jobos init
```

`jobos init` asks what roles you want, where you want them (cities, a radius around home, remote), and how much experience a job can require. It saves your answers to `config/settings.json`. Run it again anytime to change them.

Then point it at a company's job board:

```bash
jobos scout https://boards.greenhouse.io/<company> --fetch
```

```
FIT  Acme | Validation Engineer, New Grad | Austin, TX
     https://boards.greenhouse.io/acme/jobs/123
FIT  Acme | Test Engineer I | Remote - US
     https://boards.greenhouse.io/acme/jobs/456
     - must be able to obtain a security clearance
3 of 412 shown, 371 outside your target roles/locations
```

Without `--fetch` it checks titles and locations only, which is fast. With `--fetch` it reads every remaining posting in full.

**Don't know which companies to try?** Search LinkedIn in your browser (no login needed), copy the search page's URL, and scout that:

```bash
jobos scout "https://www.linkedin.com/jobs/search/?keywords=data%20analyst&location=Tampa%2C%20FL" --fetch
jobos screen https://www.linkedin.com/jobs/view/<id>    # also finds the job on the company's own site
```

It reads at most 50 results per search, one request every 1.5 seconds. Apply on the company's site, not through LinkedIn.

**See it all:** `jobos dashboard` writes `dashboard.html`, a page you open in your browser. It shows a map of your jobs (with your radius, if you set one), your pipeline (Applied, Interviewing, Rejected...), and which follow-ups are due.

## Everyday commands

| Command | What it does |
|---|---|
| `jobos` | The menu (setup, find jobs, see jobs, update a job) |
| `jobos search` | Search LinkedIn for your saved roles and places, and add the fits to your tracker |
| `jobos scout <board-url> [--fetch] [--all]` | List jobs on a board that match you (`--all` shows skips and why) |
| `jobos screen <posting-url>` | Check one posting in depth |
| `jobos add --company C --title T --url U` | Start tracking a job |
| `jobos update <id> --status Applied --applied 2026-10-08` | Record progress (notes are appended, never overwritten) |
| `jobos find <text>` / `jobos summary` | Search the tracker / count by status |
| `jobos check <company>` | Would applying now break one of your pacing rules? |
| `jobos dashboard` | Map + pipeline + follow-ups page (`dashboard.html`) |
| `jobos export apps.xlsx` | Spreadsheet of everything you acted on (`pip install -e .[xlsx]`) |
| `jobos queue add/next/done` | Shared to-apply list when several agents work at once |

Board URLs that work: `boards.greenhouse.io/<co>`, `jobs.lever.co/<co>`, `jobs.ashbyhq.com/<co>`, `<co>.wd5.myworkdayjobs.com/<site>`, Oracle Cloud career sites, `careers.smartrecruiters.com/<Co>`, `apply.workable.com/<co>`, and `amazon.jobs`.

## Your data stays on your machine

Everything lives in `~/job-search-os/data` and `~/job-search-os/config`. When you run it inside a checkout of this repo, it uses `./data` and `./config` instead, which are gitignored. Set `JOBOS_HOME` and `JOBOS_CONFIG` to keep them somewhere else. Nothing is uploaded anywhere.

## Using it with an AI agent

Tell your agent to read [AGENTS.md](AGENTS.md). It explains the workflow and the ground rules: never invent experience, read the full posting before applying, and stop for a human at anything the agent can't answer truthfully.

## Contributing

```bash
python -m pip install -e .[dev]
python -m pytest
```

Tests run on Windows, macOS, and Linux in CI. New board adapters are welcome; see `jobos/adapters/greenhouse.py` for a small example.

MIT licensed.
