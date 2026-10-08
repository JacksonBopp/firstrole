# AGENTS.md

Instructions for any AI agent (Claude Code, Codex, Cursor, Gemini, local models) helping someone job-hunt with this repo.

## First run
If `config/settings.json` does not exist, run `jobos init` with the user. It asks questions; relay them and enter the user's answers. Do not guess them.

## Workflow
1. **Find:** `jobos scout <board-url> --fetch`. It already filters by the user's roles, locations, experience, and eligibility.
2. **Read:** open each FIT posting in full before recommending it. The screener is a first pass, not a verdict. Report pay, required vs. preferred qualifications, and anything unusual (clearance, relocation, start date, on-site days).
3. **Shortlist:** recommend a few strong fits, not a long list. Say why each one fits, citing the posting.
4. **Track:** `jobos add --company C --title T --url U --note "why it fits"` for each one the user keeps.
5. **Check pacing:** run `jobos check <company>` before applying. If it reports a rule violation, stop. Do not work around it.
6. **Apply:** only if the user asked you to. Fill forms from the user's resume and stated answers. After a confirmation page, run `jobos update <id> --status Applied --applied <YYYY-MM-DD>`.
7. **Several agents at once:** use the shared queue. `jobos queue next --claim <agent-name>` claims one job, and `jobos queue done|block|skip <id> --note ...` finishes it.

## Ground rules
- **Never invent experience, skills, degrees, or motivations.** Use only what is in the user's resume or what the user told you. If a question needs something you don't have, stop and ask.
- **The user decides what gets submitted.** Get explicit permission before any final Submit, email, or message to an employer. Pause for anything you can't answer truthfully: essays, extra agreements, assessments, or identity verification.
- **Never take timed assessments or live interviews for the user.** Coach before or after, not during.
- **Mark Applied only after a confirmation page,** or when the user confirms it.
- **Keep secrets out of logs and commits.** Passwords, demographic answers, and personal details live in the user's private files, never in the repo or in chat transcripts.
- Use the `jobos` commands to change data. Never hand-edit `data/tracker.csv`: ids, notes, and the rules depend on them.

## Repo notes for coding agents
- Python 3.10+, standard library plus `certifi`. Must work on Windows, macOS, and Linux. Use `pathlib`, write files as UTF-8, and don't shell out to `python3`.
- Tests: `python -m pytest`. Add a test with every screening or targeting change, ideally paraphrased from a real posting.
- Board adapters live in `jobos/adapters/`. Use each board's public JSON API. Raise `NotFound` for a closed or missing posting; let other errors raise.
