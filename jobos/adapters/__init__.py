"""Job-board adapters. Each one turns a board's public API into the same `Posting` shape.

    from jobos.adapters import detect, fetch_posting, list_postings
    adapter = detect("https://boards.greenhouse.io/acme/jobs/123")
    posting = fetch_posting("https://boards.greenhouse.io/acme/jobs/123")
    jobs = list_postings("https://boards.greenhouse.io/acme")      # a whole board

Adding a board = one module with `matches(url)`, `list_postings(url)` and `fetch_posting(url)`.
"""
from __future__ import annotations

from . import amazon, ashby, greenhouse, lever, linkedin, oracle, smartrecruiters, workable, workday
from .base import NotFound, Posting

ADAPTERS = [greenhouse, lever, ashby, workday, oracle, amazon, smartrecruiters, workable, linkedin]


def detect(url: str):
    for a in ADAPTERS:
        if a.matches(url):
            return a
    raise ValueError(f"No adapter for {url}. Supported: Greenhouse, Lever, Ashby, Workday, Oracle Cloud, Amazon, SmartRecruiters, Workable, LinkedIn search")


def fetch_posting(url: str) -> Posting:
    return detect(url).fetch_posting(url)


def list_postings(url: str, search: str = "") -> list[Posting]:
    return detect(url).list_postings(url, search)


__all__ = ["Posting", "detect", "fetch_posting", "list_postings", "ADAPTERS"]
