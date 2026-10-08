"""Workday: <tenant>.wd<N>.myworkdayjobs.com/[<locale>/]<site>/job/<path>

Uses the same public "cxs" JSON endpoints the career site itself calls. Listing returns
titles only; call fetch_posting for the description.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .base import NotFound, Posting, html_to_text, http_json

NAME = "workday"
_LOCALE = re.compile(r"^[a-z]{2}-[A-Z]{2}$")


def matches(url: str) -> bool:
    return "myworkdayjobs.com" in urlsplit(url).netloc


def _split(url: str) -> tuple[str, str, str, str]:
    """-> (host, tenant, site, '/job/...' path or '')"""
    u = urlsplit(url)
    parts = [p for p in u.path.split("/") if p]
    if parts and _LOCALE.match(parts[0]):
        parts = parts[1:]
    if not parts:
        raise ValueError(f"Can't find the Workday site name in {url}")
    site, rest = parts[0], parts[1:]
    for tail in ("apply", "applyManually", "useMyLastApplication", "autofillWithResume"):
        if rest and rest[-1] == tail:
            rest = rest[:-1]
    return u.netloc, u.netloc.split(".")[0], site, ("/" + "/".join(rest)) if rest else ""


def list_postings(url: str, search: str = "", limit: int = 100) -> list[Posting]:
    host, tenant, site, _ = _split(url)
    out, offset = [], 0
    while offset < limit:
        data = http_json(f"https://{host}/wday/cxs/{tenant}/{site}/jobs",
                         data={"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": search})
        jobs = data.get("jobPostings", [])
        for j in jobs:
            out.append(Posting(company=tenant, title=j.get("title", ""), url=f"https://{host}/{site}{j['externalPath']}",
                               location=j.get("locationsText", ""), posted=j.get("postedOn", ""), source=NAME))
        if len(jobs) < 20:
            break
        offset += 20
    return out


def fetch_posting(url: str) -> Posting:
    host, tenant, site, path = _split(url)
    if not path.startswith("/job/"):
        raise ValueError(f"Not a Workday job URL: {url}")
    try:
        info = http_json(f"https://{host}/wday/cxs/{tenant}/{site}{path}").get("jobPostingInfo") or {}
    except NotFound:
        return Posting(company=tenant, title="", url=url, source=NAME, is_open=False)
    return Posting(company=tenant, title=info.get("title", ""), url=f"https://{host}/{site}{path}",
                   location=info.get("location", ""), text=html_to_text(info.get("jobDescription")),
                   posted=info.get("startDate", ""), source=NAME, is_open=bool(info.get("canApply", True)))
