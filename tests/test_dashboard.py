"""Dashboard: one self-contained HTML page; job-board text must never become markup."""
import json
import re

import pytest

from jobos import cli, dashboard
from jobos.targeting import Targets


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBOS_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("JOBOS_CONFIG", str(tmp_path / "config"))
    return tmp_path


ROWS = [  # made-up rows only
    {"company": "Acme Robotics", "title": "Test Engineer I", "location": "Tampa, FL", "status": "Applied",
     "date_applied": "2026-01-02", "follow_up": "2026-01-16", "url": "https://jobs.example.com/1", "notes": "n"},
    {"company": "Globex", "title": "Data Analyst", "location": "Remote - US", "status": "Rejected",
     "url": "javascript:alert(1)", "notes": ""},
    {"company": "Initech", "title": "Systems Analyst", "location": "Orlando, FL; Tampa, FL",
     "status": "Skipped - no visa", "url": "https://jobs.example.com/3"},
]


def _data(html: str) -> dict:
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1))


def test_writes_page_with_rows_pins_and_stages(tmp_path):
    out = dashboard.write(ROWS, tmp_path / "d.html", Targets())
    html = out.read_text(encoding="utf-8")
    d = _data(html)
    assert [j["company"] for j in d["jobs"]] == ["Acme Robotics", "Globex", "Initech"]
    acme, globex, initech = d["jobs"]
    assert acme["lat"] and acme["stage"] == "Applied"
    assert globex["lat"] is None                         # remote: listed, not pinned
    assert initech["stage"] == "Skipped" and initech["lat"]   # first segment (Orlando) placed
    assert globex["url"] == ""                            # javascript: link dropped
    assert d["center"] is None and d["radius_miles"] is None
    assert 'integrity="sha512-' in html and "leaflet" in html


def test_hostile_text_is_escaped(tmp_path):
    evil = [{"company": "Evil & Co", "title": '</script><img src=x onerror=alert(1)>', "location": "",
             "status": "Applied", "notes": "<!--   -->"}]
    html = dashboard.render(evil, Targets())
    assert "<img" not in html and "onerror=alert(1)>" not in html
    assert html.count("</script>") == html.count("<script")          # nothing closed early
    assert _data(html)["jobs"][0]["title"].startswith("</script><img")  # round-trips as plain text
    assert "innerHTML" not in html                                    # rendered with textContent only


def test_radius_circle_only_with_center_and_radius():
    d = dashboard.snapshot(ROWS, Targets(center=[27.976, -82.503], radius_miles=10))
    assert d["center"] == [27.976, -82.503] and d["radius_miles"] == 10
    assert dashboard.snapshot(ROWS, Targets(radius_miles=10))["radius_miles"] is None


def test_cli_works_with_no_settings_and_empty_tracker(tmp_path, capsys):
    out = tmp_path / "page.html"
    assert cli.main(["dashboard", str(out)]) == 0
    assert out.exists() and _data(out.read_text(encoding="utf-8"))["jobs"] == []
    assert "Wrote" in capsys.readouterr().out
