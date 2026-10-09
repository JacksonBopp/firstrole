"""LinkedIn public job search, logged out (the same pages anyone sees without an account).

    jobos scout "https://www.linkedin.com/jobs/search/?keywords=test%20engineer&location=Austin%2C%20TX&f_TPR=r604800"
    jobos screen https://www.linkedin.com/jobs/view/4475166287

Low volume on purpose: a few pages per search with a pause between them, and it stops at the first
"slow down" (HTTP 429). LinkedIn hides the real apply link from logged-out visitors, so
`company_board()` looks for the same job on the company's own Greenhouse / Lever / Ashby board.
Apply there, not through LinkedIn.
"""
from __future__ import annotations

import re
import time
import urllib.error
from urllib.parse import parse_qs, urlsplit

from .base import NotFound, Posting, html_to_text, http_text

NAME = "linkedin"
BASE = "https://www.linkedin.com/jobs-guest/jobs/api"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"   # the guest pages reject unknown agents
MAX_PAGES = 5                                               # 10 results each
PAUSE = 1.5
# Search filters passed through from a pasted URL. LinkedIn's experience filter (f_E) is left out on
# purpose: its "Entry level" tag is unreliable, and the screener reads the real requirements instead.
FILTERS = ("keywords", "location", "geoId", "distance", "f_TPR", "f_WT", "f_JT")


def matches(url: str) -> bool:
    return urlsplit(url).netloc.endswith("linkedin.com")


_last = 0.0


def _get(path: str, params: dict | None = None) -> str:
    """Every LinkedIn request goes through here, at most one per PAUSE seconds."""
    global _last
    time.sleep(max(0.0, _last + PAUSE - time.monotonic()))
    try:
        return http_text(f"{BASE}/{path}", params=params, ua=BROWSER_UA, retries=1)
    finally:
        _last = time.monotonic()


def _job_id(url: str) -> str | None:
    q = parse_qs(urlsplit(url).query)
    if "currentJobId" in q:
        return q["currentJobId"][0]
    m = re.search(r"/jobs/view/(?:[^/]*-)?(\d+)", urlsplit(url).path)
    return m.group(1) if m else None


def _find(pattern: str, s: str) -> str:
    m = re.search(pattern, s, re.S)
    return html_to_text(m.group(1)) if m else ""


def _cards(page: str) -> list[Posting]:
    out = []
    for card in page.split("<li")[1:]:
        jid = re.search(r"urn:li:jobPosting:(\d+)", card)
        if not jid:
            continue
        out.append(Posting(
            company=_find(r'base-search-card__subtitle">(.*?)</h4>', card),
            title=_find(r'base-search-card__title">(.*?)</h3>', card),
            location=_find(r'job-search-card__location">(.*?)</span>', card),
            posted=_find(r'datetime="([^"]+)"', card),
            url=f"https://www.linkedin.com/jobs/view/{jid.group(1)}", source=NAME))
    return out


def list_postings(url: str, search: str = "", pages: int = MAX_PAGES) -> list[Posting]:
    q = parse_qs(urlsplit(url).query)
    params = {k: q[k][0] for k in FILTERS if k in q}
    if search:
        params["keywords"] = search
    if not params.get("keywords"):
        raise ValueError("Give a LinkedIn search URL with keywords=..., or add --search \"job title\"")
    out: list[Posting] = []
    for page in range(pages):
        try:
            html = _get("seeMoreJobPostings/search", {**params, "start": page * 10})
        except urllib.error.HTTPError as e:
            if e.code == 429 and out:
                break                               # asked to slow down: keep what we have
            raise
        except NotFound:
            break
        cards = _cards(html)
        out += [c for c in cards if c.url not in {o.url for o in out}]
        if len(cards) < 10:
            break
    return out


def fetch_posting(url: str) -> Posting:
    jid = _job_id(url)
    if not jid:
        raise ValueError(f"No LinkedIn job id in {url}")
    try:
        s = _get(f"jobPosting/{jid}")
    except NotFound:
        return Posting(company="", title="", url=url, source=NAME, is_open=False)
    criteria = dict(re.findall(r'job-criteria-subheader">\s*(.*?)\s*<.*?job-criteria-text[^>]*>\s*(.*?)\s*<', s, re.S))
    return Posting(
        company=_find(r'topcard__org-name-link[^>]*>(.*?)</a>', s) or _find(r'topcard__flavor">(.*?)</span>', s),
        title=_find(r'top-card-layout__title[^>]*>(.*?)</h2>', s),
        location=_find(r'topcard__flavor--bullet">(.*?)</span>', s),
        text=_find(r'show-more-less-html__markup[^>]*>(.*?)</div>', s),
        url=f"https://www.linkedin.com/jobs/view/{jid}", source=NAME,
        is_open="No longer accepting applications" not in s,
        extra={k.lower(): v for k, v in criteria.items()})


_SUFFIX = re.compile(r"(?i)[,.]?\s+(inc|llc|ltd|corp|corporation|co|company|technologies|group|usa|us)\.?$")


def _slugs(company: str) -> list[str]:
    name = company.strip()
    for _ in range(2):
        name = _SUFFIX.sub("", name)
    low = name.lower()
    return list(dict.fromkeys(s for s in (re.sub(r"[^a-z0-9]", "", low), re.sub(r"[^a-z0-9]+", "-", low).strip("-")) if s))


def _same_title(a: str, b: str) -> bool:
    n = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()      # noqa: E731
    return n(a) == n(b) or (len(n(a)) > 8 and (n(a) in n(b) or n(b) in n(a)))


def company_board(company: str, title: str) -> str | None:
    """The same job on the company's own board, by guessing its Greenhouse/Lever/Ashby name. None if not found."""
    from . import ashby, greenhouse, lever
    boards = [(greenhouse, "https://boards.greenhouse.io/{}"), (lever, "https://jobs.lever.co/{}"),
              (ashby, "https://jobs.ashbyhq.com/{}")]
    for slug in _slugs(company):
        for mod, pattern in boards:
            try:
                jobs = mod.list_postings(pattern.format(slug))
            except Exception:                        # no such board: try the next guess
                continue
            hit = next((j for j in jobs if _same_title(j.title, title)), None)
            if hit:
                return hit.url
    return None
