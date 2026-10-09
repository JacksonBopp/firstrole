# firstrole

**Land your first role.** A free job-search helper for new grads and career starters, no AI subscription needed.

[![tests](https://github.com/JacksonBopp/firstrole/actions/workflows/tests.yml/badge.svg)](https://github.com/JacksonBopp/firstrole/actions/workflows/tests.yml)

Find jobs you actually qualify for, track every application, and let any AI agent help, on Windows, macOS, or Linux.

- **Reads the full posting, not just the title.** It tells "3+ years required" apart from "2-5 years preferred," catches clearance, citizenship, and degree requirements, and flags postings in another language.
- **Ranks what's left, 1 to 5, and says why.** Role match, experience, location, and things to double-check. Anything under 3.5 is left out, so you see the few jobs worth your evening. No AI needed, and the same answer every time.
- **Knows the other names your job goes by.** Pick "business analyst" and it offers operations, systems, and reporting analyst too.
- **Pulls from company job boards directly:** Greenhouse, Lever, Ashby, Workday, Oracle Cloud, SmartRecruiters, Workable, and Amazon, through their public APIs. Optional LinkedIn search reads its public logged-out pages, slowly. No login, no API keys.
- **One tracker, one source of truth.** A plain CSV that you can open in Excel, plus pacing rules (for example, at most 3 applications per company) that every agent has to follow.
- **Works with any AI tool, or none.** It's an ordinary command-line tool, so Claude Code, Codex, Cursor, Gemini, or a local model can run it, and so can you.

## Easiest: use it inside Claude (nothing to install)

Start a Claude chat (the free plan works; so do ChatGPT and Gemini) and send:

```text
Read https://raw.githubusercontent.com/JacksonBopp/firstrole/main/chat/prompt.md and follow it to help me find a job.
```

See [chat/START_HERE.md](chat/START_HERE.md) for tips. Claude asks what you're looking for, searches the web, reads every posting in full, applies the same screening rules as this tool, and keeps your tracker as a table.

The app below does the same thing on your own computer, with more reliable search, a map, and a tracker that saves itself.

## Start here: the app (no coding needed)

**1. Paste one line.**

- **Windows:** press Start, type `PowerShell`, press Enter, then paste this and press Enter:
  ```
  irm https://raw.githubusercontent.com/JacksonBopp/firstrole/main/install.ps1 | iex
  ```
- **Mac:** press Cmd+Space, type `Terminal`, press Enter, then paste this and press Enter:
  ```
  curl -fsSL https://raw.githubusercontent.com/JacksonBopp/firstrole/main/install.sh | sh
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

> **Using the Claude or ChatGPT chat app?** It can't install the app for you, because chat apps run in a sandbox, not on your computer. Paste the line above yourself (about two minutes), or use the [chat prompt](chat/START_HERE.md) instead. (Claude Code, Codex, and Cursor *can* run it for you: see [Using it with an AI agent](#using-it-with-an-ai-agent).)

Your job list stays on your computer, in a `firstrole` folder in your home folder. To update, paste the same line again.

## Quick start for developers

Needs Python 3.10+.

```bash
git clone https://github.com/JacksonBopp/firstrole.git
cd firstrole
python -m pip install -e .
firstrole init
```

`firstrole init` asks what roles you want, where you want them (cities, a radius around home, remote), and how much experience a job can require. It saves your answers to `config/settings.json`. Run it again anytime to change them.

Then point it at a company's job board:

```bash
firstrole scout https://boards.greenhouse.io/<company> --fetch
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
firstrole scout "https://www.linkedin.com/jobs/search/?keywords=data%20analyst&location=Tampa%2C%20FL" --fetch
firstrole screen https://www.linkedin.com/jobs/view/<id>    # also finds the job on the company's own site
```

It reads at most 50 results per search, one request every 1.5 seconds. Apply on the company's site, not through LinkedIn.

**See it all:** `firstrole dashboard` writes `dashboard.html`, a page you open in your browser. It shows a map of your jobs (with your radius, if you set one), your pipeline (Applied, Interviewing, Rejected...), and which follow-ups are due.

## Everyday commands

| Command | What it does |
|---|---|
| `firstrole` | The menu (setup, find jobs, see jobs, update a job) |
| `firstrole search` | Search LinkedIn for your saved roles and places, and add the fits to your tracker |
| `firstrole scout <board-url> [--fetch] [--all]` | List jobs on a board that match you (`--all` shows skips and why) |
| `firstrole screen <posting-url>` | Check one posting in depth |
| `firstrole add --company C --title T --url U` | Start tracking a job |
| `firstrole update <id> --status Applied --applied 2026-10-08` | Record progress (notes are appended, never overwritten) |
| `firstrole find <text>` / `firstrole summary` | Search the tracker / count by status |
| `firstrole check <company>` | Would applying now break one of your pacing rules? |
| `firstrole dashboard` | Map + pipeline + follow-ups page (`dashboard.html`) |
| `firstrole export apps.xlsx` | Spreadsheet of everything you acted on (`pip install -e .[xlsx]`) |
| `firstrole queue add/next/done` | Shared to-apply list when several agents work at once |

(Installed before the rename? `jobos` still works the same way.)

Board URLs that work: `boards.greenhouse.io/<co>`, `jobs.lever.co/<co>`, `jobs.ashbyhq.com/<co>`, `<co>.wd5.myworkdayjobs.com/<site>`, Oracle Cloud career sites, `careers.smartrecruiters.com/<Co>`, `apply.workable.com/<co>`, and `amazon.jobs`.

## Your data stays on your machine

Everything lives in `~/firstrole/data` and `~/firstrole/config`. When you run it inside a checkout of this repo, it uses `./data` and `./config` instead, which are gitignored. Set `JOBOS_HOME` and `JOBOS_CONFIG` to keep them somewhere else. Nothing is uploaded anywhere.

## Using it with an AI agent

Tell your agent to read [AGENTS.md](AGENTS.md). It explains the workflow and the ground rules: never invent experience, read the full posting before applying, and stop for a human at anything the agent can't answer truthfully.

## Contributing

```bash
python -m pip install -e .[dev]
python -m pytest
```

Tests run on Windows, macOS, and Linux in CI. New board adapters are welcome; see `jobos/adapters/greenhouse.py` for a small example.

MIT licensed.
