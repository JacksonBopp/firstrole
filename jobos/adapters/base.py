"""Shared pieces: the Posting shape, a tiny stdlib HTTP client, and HTML-to-text."""
from __future__ import annotations

import html
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

UA = "Mozilla/5.0 (job-search-os; +https://github.com/) Python-urllib"


def _ssl_context() -> ssl.SSLContext:
    """Prefer certifi's CA bundle (what requests uses); fall back to the OS store.
    Some Windows Python installs can't verify common sites with the OS store alone."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_CTX = _ssl_context()


class NotFound(Exception):
    """The posting is gone (HTTP 404/410). Anything else is a real error and is raised."""


@dataclass
class Posting:
    company: str
    title: str
    url: str
    location: str = ""
    text: str = ""            # full description as plain text ("" when only listed, not fetched)
    source: str = ""          # adapter name
    posted: str = ""
    is_open: bool = True
    extra: dict = field(default_factory=dict)


def http_json(url: str, *, data: dict | None = None, params: dict | None = None, retries: int = 2) -> dict | list:
    return json.loads(http_text(url, data=data, params=params, retries=retries, accept="application/json"))


def http_text(url: str, *, data: dict | None = None, params: dict | None = None, retries: int = 2,
              accept: str = "text/html", ua: str = UA) -> str:
    if params:
        from urllib.parse import urlencode
        url += ("&" if "?" in url else "?") + urlencode(params)
    body = json.dumps(data).encode() if data is not None else None
    headers = {"User-Agent": ua, "Accept": accept}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body is not None else "GET")
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30, context=_CTX) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                raise NotFound(url) from e
            if e.code in (429, 503) and attempt < retries:   # polite backoff
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError as e:
            if isinstance(e.reason, ssl.SSLCertVerificationError):
                raise RuntimeError("SSL certificate check failed. Fix: pip install certifi") from e
            raise
    raise RuntimeError("unreachable")


_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"(?i)<\s*(br|/p|/li|/h\d|/div)\s*/?>")


def html_to_text(s: str | None) -> str:
    """Strip HTML but keep line breaks, so section headings stay detectable."""
    if not s:
        return ""
    s = html.unescape(s)                    # some boards double-escape
    s = _BLOCK.sub("\n", s)
    s = html.unescape(_TAG.sub(" ", s))
    s = re.sub(r"[ \t\xa0]+", " ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()
