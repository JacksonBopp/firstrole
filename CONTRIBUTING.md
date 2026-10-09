# Contributing to firstrole

Thanks for helping! Bug reports from people who aren't programmers are just as welcome as code.

## Found a problem?
Open an issue with the **Bug report** template. Tell us what you clicked or typed, what you expected, and what happened.
**Never paste personal information:** no resume, address, phone number, or your `settings.json` or `tracker.csv`.

## Have a question?
Ask in [Discussions](https://github.com/JacksonBopp/firstrole/discussions).

## Changing code
```bash
git clone https://github.com/JacksonBopp/firstrole.git
cd firstrole
python -m pip install -e .[dev]
python -m pytest
```
- It must work on Windows, macOS, and Linux: use `pathlib`, write files as UTF-8, and don't call `python3` directly.
- Add a test with every screening, scoring, or targeting change, ideally paraphrased from a real posting. Tests never touch the network or real personal data.
- New job boards go in `jobos/adapters/` (see `greenhouse.py`). Use the board's public API, and raise `NotFound` for closed postings.
- The ground rules in [AGENTS.md](AGENTS.md) apply to code too: nothing may invent experience or submit for a user without their approval.
