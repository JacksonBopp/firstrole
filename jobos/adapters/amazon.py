"""Amazon: amazon.jobs/en/jobs/<id>/<slug>. Uses the site's search.json endpoint.

Gotcha: the job id in the URL is the source of truth. Titles can change and one person's
notes once recorded a different role under the same id, so always match on id.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .base import Posting, html_to_text, http_json

NAME = "amazon"
_SEARCH = "https://www.amazon.jobs/en/search.json"


def matches(url: str) -> bool:
    return "amazon.jobs" in urlsplit(url).netloc


def _posting(j: dict) -> Posting:
    text = "\n".join(filter(None, [html_to_text(j.get("description")),
                                   "BASIC QUALIFICATIONS\n" + html_to_text(j.get("basic_qualifications")),
                                   "PREFERRED QUALIFICATIONS\n" + html_to_text(j.get("preferred_qualifications"))]))
    return Posting(company="Amazon", title=j.get("title", ""), url="https://www.amazon.jobs" + j.get("job_path", ""),
                   location=j.get("normalized_location") or j.get("location", ""), text=text,
                   posted=j.get("posted_date", ""), source=NAME, extra={"id": j.get("id_icims")})


def list_postings(url: str = "", search: str = "", location: str = "", limit: int = 100) -> list[Posting]:
    params = {"base_query": search, "result_limit": min(limit, 100)}
    if location:
        params["loc_query"] = location
    return [_posting(j) for j in http_json(_SEARCH, params=params).get("jobs", [])]


def fetch_posting(url: str) -> Posting:
    m = re.search(r"/jobs/(\d+)(?:/([^/?#]+))?", url)
    if not m:
        raise ValueError(f"No Amazon job id in {url}")
    jid, slug = m.group(1), (m.group(2) or "").replace("-", " ")
    for q in filter(None, [slug[:80], " ".join(slug.split()[:4]), jid]):
        for j in http_json(_SEARCH, params={"base_query": q, "result_limit": 100}).get("jobs", []):
            if str(j.get("id_icims")) == jid:
                return _posting(j)
    return Posting(company="Amazon", title="", url=url, source=NAME, is_open=False)
