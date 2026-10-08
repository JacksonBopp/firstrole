"""Ashby: jobs.ashbyhq.com/<org>/<job-uuid>."""
from __future__ import annotations

from urllib.parse import unquote, urlsplit

from .base import Posting, html_to_text, http_json

NAME = "ashby"


def matches(url: str) -> bool:
    return "ashbyhq.com" in urlsplit(url).netloc


def _parts(url: str) -> list[str]:
    return [unquote(p) for p in urlsplit(url).path.split("/") if p and p != "application"]


def _posting(org: str, j: dict) -> Posting:
    comp = (j.get("compensation") or {}).get("compensationTierSummary")
    return Posting(company=org, title=j.get("title", ""), url=j.get("jobUrl", ""), source=NAME,
                   location=j.get("location", ""), text=html_to_text(j.get("descriptionHtml")),
                   posted=(j.get("publishedAt") or "")[:10], extra={"salary": comp} if comp else {})


def _board(org: str) -> list[dict]:
    data = http_json(f"https://api.ashbyhq.com/posting-api/job-board/{org}", params={"includeCompensation": "true"})
    return data.get("jobs", [])


def list_postings(url: str, search: str = "") -> list[Posting]:
    org = _parts(url)[0]
    jobs = [_posting(org, j) for j in _board(org)]
    s = search.lower()
    return [p for p in jobs if s in p.title.lower()] if s else jobs


def fetch_posting(url: str) -> Posting:
    parts = _parts(url)
    if len(parts) < 2:
        raise ValueError(f"No Ashby job id in {url}")
    for j in _board(parts[0]):
        if j.get("id") == parts[1]:
            return _posting(parts[0], j)
    return Posting(company=parts[0], title="", url=url, source=NAME, is_open=False)
