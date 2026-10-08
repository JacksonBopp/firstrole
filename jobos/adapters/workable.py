"""Workable: apply.workable.com/<account>/j/<shortcode>, or <account>.workable.com.

The board endpoint returns full descriptions, so listing needs no extra calls.
"""
from __future__ import annotations

from urllib.parse import unquote, urlsplit

from .base import NotFound, Posting, html_to_text, http_json

NAME = "workable"


def matches(url: str) -> bool:
    return urlsplit(url).netloc.endswith("workable.com")


def _parts(url: str) -> tuple[str, str | None]:
    """(account, shortcode or None)."""
    u = urlsplit(url)
    parts = [unquote(p) for p in u.path.split("/") if p]
    host = u.netloc.split(".")[0]
    account = host if host not in ("apply", "www", "jobs") else (parts[0] if parts and parts[0] != "j" else "")
    code = parts[parts.index("j") + 1] if "j" in parts and parts.index("j") + 1 < len(parts) else None
    if not account:
        raise ValueError(f"{url} has no company name in it. Use apply.workable.com/<company>/j/<code>")
    return account, code


def _location(j: dict) -> str:
    loc = (j.get("locations") or [j])[0]
    where = ", ".join(x for x in (loc.get("city"), loc.get("region") or loc.get("state"), loc.get("country")) if x)
    return f"{where} (Remote)" if j.get("telecommuting") or j.get("remote") else where


def _board(account: str) -> dict:
    d = http_json(f"https://apply.workable.com/api/v1/widget/accounts/{account}", params={"details": "true"})
    assert isinstance(d, dict)
    return d


def list_postings(url: str, search: str = "") -> list[Posting]:
    account, _ = _parts(url)
    d = _board(account)
    jobs = [Posting(company=d.get("name") or account, title=j.get("title", ""), source=NAME,
                    url=f"https://apply.workable.com/{account}/j/{j['shortcode']}", location=_location(j),
                    text=html_to_text(j.get("description")), posted=j.get("published_on", ""))
            for j in d.get("jobs", [])]
    s = search.lower()
    return [p for p in jobs if s in p.title.lower()] if s else jobs


def fetch_posting(url: str) -> Posting:
    account, code = _parts(url)
    if not code:
        raise ValueError(f"No Workable job code in {url}")
    try:
        j = http_json(f"https://apply.workable.com/api/v2/accounts/{account}/jobs/{code}")
    except NotFound:
        return Posting(company=account, title="", url=url, source=NAME, is_open=False)
    assert isinstance(j, dict)
    text = "\n".join(html_to_text(j.get(k)) for k in ("description", "requirements", "benefits") if j.get(k))
    loc = j.get("location") or {}
    return Posting(company=account, title=j.get("title", ""), url=f"https://apply.workable.com/{account}/j/{code}",
                   location=_location({**j, "locations": [loc]}), text=text, source=NAME,
                   posted=(j.get("published") or "")[:10], is_open=j.get("state", "published") == "published")
