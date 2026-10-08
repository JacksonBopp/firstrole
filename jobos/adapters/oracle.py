"""Oracle Recruiting Cloud: <host>.oraclecloud.com/hcmUI/CandidateExperience/<lang>/sites/<site>/job/<id>

Gotcha worth knowing: some employers put the real experience requirement in a custom
"flex field" (e.g. "Years of Experience: 3-5") that never appears in the description text.
We append those fields to the text so screening sees them.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .base import Posting, html_to_text, http_json

NAME = "oracle"
_REQ = "/hcmRestApi/resources/latest"


def matches(url: str) -> bool:
    return "oraclecloud.com" in urlsplit(url).netloc and "CandidateExperience" in url


def _split(url: str) -> tuple[str, str, str | None]:
    u = urlsplit(url)
    m = re.search(r"/sites/([^/]+)", u.path)
    if not m:
        raise ValueError(f"Can't find the Oracle site in {url}")
    j = re.search(r"/job/(\d+)", u.path)
    return u.netloc, m.group(1), j.group(1) if j else None


def list_postings(url: str, search: str = "", limit: int = 100) -> list[Posting]:
    host, site, _ = _split(url)
    finder = f'findReqs;siteNumber={site},keyword="{search}",limit={min(limit, 200)},sortBy=POSTING_DATES_DESC'
    data = http_json(f"https://{host}{_REQ}/recruitingCEJobRequisitions",
                     params={"onlyData": "true", "expand": "requisitionList", "finder": finder})
    items = (data.get("items") or [{}])[0].get("requisitionList", [])
    return [Posting(company=host.split(".")[0], title=r.get("Title", ""), location=r.get("PrimaryLocation", ""),
                    url=f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{r.get('Id')}",
                    posted=(r.get("PostedDate") or "")[:10], source=NAME) for r in items]


def fetch_posting(url: str) -> Posting:
    host, site, jid = _split(url)
    if not jid:
        raise ValueError(f"No Oracle job id in {url}")
    data = http_json(f"https://{host}{_REQ}/recruitingCEJobRequisitionDetails",
                     params={"expand": "all", "onlyData": "true", "finder": f'ById;Id="{jid}",siteNumber={site}'})
    items = data.get("items") or []
    if not items:
        return Posting(company=host.split(".")[0], title="", url=url, source=NAME, is_open=False)
    it = items[0]
    text = "\n".join(html_to_text(it.get(k)) for k in
                     ("ExternalDescriptionStr", "ExternalResponsibilitiesStr", "ExternalQualificationsStr") if it.get(k))
    flex = [f"{f.get('Prompt')}: {f.get('Value')}" for f in it.get("requisitionFlexFields", []) if f.get("Value")]
    if flex:
        text += "\nAdditional requirements:\n" + "\n".join(flex)
    return Posting(company=host.split(".")[0], title=it.get("Title", ""), url=url, text=text,
                   location=it.get("PrimaryLocation", ""), posted=(it.get("ExternalPostedStartDate") or "")[:10],
                   source=NAME, extra={"flex_fields": flex})
