"""SmartRecruiters: jobs.smartrecruiters.com/<Company>/<id>-<slug>, careers.smartrecruiters.com/<Company>.

The list endpoint has titles and locations only; descriptions come from one call per posting (`--fetch`).
"""
from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from .base import NotFound, Posting, html_to_text, http_json

NAME = "smartrecruiters"
API = "https://api.smartrecruiters.com/v1/companies"
MAX_LIST = 1000                     # big boards (Bosch: ~5000) -> use --search to narrow


def matches(url: str) -> bool:
    return "smartrecruiters.com" in urlsplit(url).netloc


def _parts(url: str) -> tuple[str, str | None]:
    """(company, posting id or None) from a jobs./careers./api. URL."""
    parts = [unquote(p) for p in urlsplit(url).path.split("/") if p]
    if parts[:2] == ["v1", "companies"]:                   # api.../v1/companies/<Co>/postings/<id>
        parts = [p for p in parts[2:] if p != "postings"]
    if not parts:
        raise ValueError(f"No SmartRecruiters company in {url}")
    m = re.match(r"\d+", parts[1]) if len(parts) > 1 else None
    return parts[0], m.group(0) if m else None


def _location(loc: dict) -> str:
    raw = loc.get("fullLocation") or ", ".join((loc.get("city") or "", loc.get("region") or "", loc.get("country") or ""))
    where = ", ".join(x.strip() for x in raw.split(",") if x.strip())     # "Ho Chi Minh, , Vietnam"
    return f"{where} (Remote)" if loc.get("remote") else where


def _summary(company: str, j: dict) -> Posting:
    return Posting(company=company, title=j.get("name", "").strip(), source=NAME,
                   url=f"https://jobs.smartrecruiters.com/{company}/{j['id']}",
                   location=_location(j.get("location") or {}), posted=(j.get("releasedDate") or "")[:10])


def list_postings(url: str, search: str = "") -> list[Posting]:
    company, _ = _parts(url)
    out: list[Posting] = []
    while len(out) < MAX_LIST:
        params: dict[str, object] = {"limit": 100, "offset": len(out)}
        if search:
            params["q"] = search
        page = http_json(f"{API}/{company}/postings", params=params)
        assert isinstance(page, dict)
        out += [_summary(company, j) for j in page.get("content", [])]
        if not page.get("content") or len(out) >= page.get("totalFound", 0):
            break
    if not out and not search:
        raise NotFound(url)                  # unknown companies return an empty list, not a 404
    s = search.lower()                       # `q` also matches descriptions; keep title matches like other boards
    return [p for p in out if s in p.title.lower()] if s else out


def fetch_posting(url: str) -> Posting:
    company, pid = _parts(url)
    if not pid:
        raise ValueError(f"No SmartRecruiters posting id in {url}")
    try:
        d = http_json(f"{API}/{company}/postings/{pid}")
    except NotFound:
        return Posting(company=company, title="", url=url, source=NAME, is_open=False)
    assert isinstance(d, dict)
    sections = (d.get("jobAd") or {}).get("sections") or {}
    text = "\n".join(f"{s.get('title', '')}\n{html_to_text(s.get('text'))}" for k, s in sections.items()
                     if k != "videos" and s.get("text"))
    p = _summary(company, d)
    p.company = (d.get("company") or {}).get("name") or company
    p.url = d.get("postingUrl") or p.url
    p.text, p.is_open = text, bool(d.get("active", True))
    level = (d.get("experienceLevel") or {}).get("label")
    if level:
        p.extra["level"] = level
    return p
