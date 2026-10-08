"""Greenhouse: boards.greenhouse.io/<board>, job-boards.greenhouse.io/<board>, plus the EU host."""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .base import NotFound, Posting, html_to_text, http_json

NAME = "greenhouse"


def matches(url: str) -> bool:
    return "greenhouse.io" in urlsplit(url).netloc or "gh_jid=" in url


def _api(url: str) -> str:
    return "https://boards-api.eu.greenhouse.io" if ".eu.greenhouse.io" in url else "https://boards-api.greenhouse.io"


def _board(url: str) -> str:
    parts = [p for p in urlsplit(url).path.split("/") if p]
    if not parts:
        raise ValueError(f"Can't find the Greenhouse board name in {url}")
    return parts[0]


def _job_id(url: str) -> str | None:
    m = re.search(r"/jobs/(\d+)", url) or re.search(r"gh_jid=(\d+)", url)
    return m.group(1) if m else None


def _posting(board: str, j: dict, with_text: bool) -> Posting:
    return Posting(company=board, title=j.get("title", ""), url=j.get("absolute_url", ""),
                   location=(j.get("location") or {}).get("name", ""), source=NAME,
                   posted=(j.get("updated_at") or "")[:10],
                   text=html_to_text(j.get("content")) if with_text else "")


def list_postings(url: str, search: str = "") -> list[Posting]:
    board = _board(url)
    data = http_json(f"{_api(url)}/v1/boards/{board}/jobs", params={"content": "true"})
    jobs = [_posting(board, j, True) for j in data.get("jobs", [])]
    s = search.lower()
    return [p for p in jobs if s in p.title.lower()] if s else jobs


def fetch_posting(url: str) -> Posting:
    board, jid = _board(url), _job_id(url)
    if not jid:
        raise ValueError(f"No Greenhouse job id in {url}")
    try:
        j = http_json(f"{_api(url)}/v1/boards/{board}/jobs/{jid}")
    except NotFound:
        return Posting(company=board, title="", url=url, source=NAME, is_open=False)
    return _posting(board, j, True)
