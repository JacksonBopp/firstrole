# job-search-os: design

A job-search operating system you run with **any AI coding agent, on any OS**. It finds entry-level roles, reads the full posting, screens for real fit, tracks everything, and fills applications in the browser, with a human approving the final Submit by default.

It is not a spam bot. Quality over quantity is the core design rule.

## Goals
1. **Any OS:** Windows, macOS, Linux. Plain Python 3.10+ and Node 18+ (for the Playwright MCP). No shell-only scripts on the critical path.
2. **Any agent:** Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, OpenCode, and others. Instructions live in the open `AGENTS.md` format; workflows are open-standard Agent Skills.
3. **Any model for screening:** an optional AI screening step speaks the OpenAI-compatible API, so it works with OpenAI, OpenRouter, Anthropic (compat endpoint), or **local models via Ollama / LM Studio**.
4. **Safe by default:** approve-before-Submit on; never invents facts; no CAPTCHA solving; per-company caps enforced in code; a screenshot and answer log for every submission.
5. **Private by default:** all personal data lives in gitignored files on the user's machine.

## Layout
```
AGENTS.md                 # the rules every agent follows (canonical)
CLAUDE.md / GEMINI.md     # one-line pointers to AGENTS.md
core/                     # plain Python, no AI required
  tracker.py              # CSV source of truth + xlsx export
  queue.py                # shared work queue (multiple agents can cooperate)
  rules.py                # code-enforced caps: per-company, same-day, skip-if-interviewing
  screen.py               # rule-based screening (years, degree, clearance, seniority)
  ai_screen.py            # optional LLM screening via OpenAI-compatible API
adapters/                 # job-board readers: Greenhouse, Lever, Ashby, Workday, Oracle, Amazon, ...
skills/                   # Agent Skills: setup, scout, apply, log, inbox-sync, interview-prep
templates/                # profile / answers / settings examples (*.example)
docs/                     # setup guides per agent and OS
```

## User config (gitignored, created by guided setup)
- `config/profile.json`: name, contact, education, links, resume paths
- `config/answers.md`: fact sheet + personal "why" answer bank (in the user's own words)
- `config/settings.json`: targets, locations, caps, approval mode, model endpoint
- `.env`: portal email and password (never read aloud, never logged)

## Differentiators vs. similar tools
- Workday / Oracle / Eightfold / Amazon support, not just Greenhouse/Lever/Ashby
- Windows first-class
- Multi-agent queue (e.g. Claude on a desktop + Codex on a laptop)
- Tracker, inbox sync, and interview tracking built in
- Local-model screening option (free to run)

## Source
Generalized from a private, personal setup. **Nothing personal is copied:** code is ported file by file and reviewed; all data, notes, and history stay in the private repo.

## Roadmap
- **Targeting** (settings-driven, never hardcoded): role keywords, locations/countries, remote, exclude list, language requirements (e.g. "Japanese required", JLPT) and visa support for roles abroad.
- **Optional LinkedIn discovery** via the public guest job search (no login, never Easy Apply; apply on the employer's own site). Do not use LinkedIn's experience-level filter: it hides most real entry roles, which are tagged "Not Applicable".
- Agent instructions (AGENTS.md) + Agent Skills; guided setup; personal "why" answer bank; screenshot + answer log per submit.
- Portability rule: never shell out to `python3` (it is a Microsoft Store stub on Windows); use `sys.executable`.
