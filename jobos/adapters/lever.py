"""Lever: jobs.lever.co/<company>/<id> (and jobs.eu.lever.co)."""
from __future__ import annotations

from urllib.parse import urlsplit

from .base import NotFound, Posting, html_to_text, http_json

NAME = "lever"


def matches(url: str) -> bool:
    return "lever.co" in urlsplit(url).netloc


def _api(url: str) -> str:
    return "https://api.eu.lever.co" if ".eu." in urlsplit(url).netloc else "https://api.lever.co"


def _parts(url: str) -> list[str]:
    return [p for p in urlsplit(url).path.split("/") if p and p != "apply"]


def _posting(company: str, j: dict) -> Posting:
    lists = " ".join(f"\n{l.get('text', '')}\n{html_to_text(l.get('content'))}" for l in j.get("lists", []))
    text = "\n".join(filter(None, [html_to_text(j.get("description")), lists, html_to_text(j.get("additional"))]))
    return Posting(company=company, title=j.get("text", ""), url=j.get("hostedUrl", ""), source=NAME,
                   location=(j.get("categories") or {}).get("location", ""), text=text,
                   extra={"salary": j.get("salaryRange")} if j.get("salaryRange") else {})


def list_postings(url: str, search: str = "") -> list[Posting]:
    company = _parts(url)[0]
    data = http_json(f"{_api(url)}/v0/postings/{company}", params={"mode": "json"})
    jobs = [_posting(company, j) for j in data] if isinstance(data, list) else []
    s = search.lower()
    return [p for p in jobs if s in p.title.lower()] if s else jobs


def fetch_posting(url: str) -> Posting:
    parts = _parts(url)
    if len(parts) < 2:
        raise ValueError(f"No Lever posting id in {url}")
    try:
        j = http_json(f"{_api(url)}/v0/postings/{parts[0]}/{parts[1]}")
    except NotFound:
        return Posting(company=parts[0], title="", url=url, source=NAME, is_open=False)
    return _posting(parts[0], j)
