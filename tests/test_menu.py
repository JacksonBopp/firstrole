"""The no-terminal-experience path: menu + search built from settings. LinkedIn is faked."""
import json

import pytest

from jobos import menu, search, tracker
from jobos.adapters.base import Posting
from jobos.screen import Profile
from jobos.targeting import Targets


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBOS_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("JOBOS_CONFIG", str(tmp_path / "config"))
    return tmp_path


def test_plan_roles_places_remote():
    t = Targets(roles=["data analyst", "business analyst"], locations=["Tampa, FL"], remote=True, radius_miles=10)
    qs = search.plan(t)
    assert len(qs) == 4
    assert {"keywords": "data analyst", "location": "Tampa, FL", "distance": "10", "f_TPR": "r2592000"} in qs
    assert any(q.get("f_WT") == "2" and q["location"] == "United States" for q in qs)
    home_only = search.plan(Targets(roles=["qa"], center=[27.976, -82.503], radius_miles=10, remote=False))
    assert home_only[0]["location"].endswith(", FL")           # nearest town to the home point
    with pytest.raises(ValueError):
        search.plan(Targets())


def _fake_linkedin(monkeypatch):
    listed = [Posting("Acme", "Data Analyst I", "https://www.linkedin.com/jobs/view/1", "Tampa, FL", source="linkedin"),
              Posting("Acme", "Senior Data Analyst", "https://www.linkedin.com/jobs/view/2", "Tampa, FL", source="linkedin"),
              Posting("Zed", "Data Analyst", "https://www.linkedin.com/jobs/view/3", "Denver, CO", source="linkedin")]
    texts = {"1": "Requirements\nBachelor's degree. 0-1 years of experience.",
             "2": "Requirements\n5+ years of experience in SQL"}
    monkeypatch.setattr(search.linkedin, "list_postings", lambda url, pages=5: listed)
    monkeypatch.setattr(search.linkedin, "fetch_posting", lambda url: Posting(
        "Acme", next(p.title for p in listed if p.url == url), url, "Tampa, FL", text=texts[url[-1]], source="linkedin"))


def test_search_adds_only_fits_once(monkeypatch):
    _fake_linkedin(monkeypatch)
    t = Targets(roles=["data analyst"], locations=["Tampa, FL"], remote=False)
    added = search.run(t, Profile(us_citizen=True), say=lambda _: None)
    assert [r["title"] for r in added] == ["Data Analyst I"]     # senior + Denver filtered out
    assert tracker.load()[0]["status"] == "Found"
    assert search.run(t, Profile(us_citizen=True), say=lambda _: None) == []   # already tracked


def test_menu_first_run_search_update_quit(isolated, monkeypatch):
    _fake_linkedin(monkeypatch)
    answers = iter(["data analyst", "", "Tampa, FL", "", "n", "", "", "2", "y", "n", "n", "3",   # setup
                    "1",            # find jobs
                    "3", "1", "1",  # update job 1 -> applied
                    "2",            # dashboard
                    "5"])
    out = []
    assert menu.run(ask=lambda _: next(answers), say=out.append, launch=False) == 0
    row = tracker.load()[0]
    assert row["status"] == "Applied" and row["date_applied"] and row["follow_up"]
    assert (isolated / "data" / "dashboard.html").exists()
    assert json.loads((isolated / "config" / "settings.json").read_text())["targets"]["roles"] == ["data analyst"]


def test_menu_ctrl_c_exits_cleanly():
    def boom(_):
        raise KeyboardInterrupt
    assert menu.run(ask=boom, say=lambda _: None, launch=False) == 0
