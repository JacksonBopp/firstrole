import json
from datetime import date

import pytest

from jobos import cli, queue, rules, tracker


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBOS_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("JOBOS_CONFIG", str(tmp_path / "config"))
    return tmp_path


TODAY = date.today().isoformat()


def test_same_posting_maps_to_one_id():
    a = "https://boards.greenhouse.io/acme/jobs/123?gh_jid=123&utm_source=linkedin"
    b = "https://boards.greenhouse.io/acme/jobs/123/?gh_jid=123"
    assert tracker.job_id(a) == tracker.job_id(b)


def test_add_rejects_duplicates_and_update_appends_notes():
    rows = []
    r = tracker.add(rows, company="Acme", title="Test Engineer", url="https://x.com/jobs/1", note="found it")
    with pytest.raises(ValueError):
        tracker.add(rows, company="Acme", title="Test Engineer", url="https://x.com/jobs/1/")
    tracker.update(rows, r["id"], status="Applied", note="submitted")
    assert r["status"] == "Applied"
    assert r["notes"].count(" | ") == 1 and "found it" in r["notes"] and "submitted" in r["notes"]


def test_update_by_id_hits_exactly_one_row():
    rows = []
    a = tracker.add(rows, company="IBM", title="SW Dev Intern: Systems Assurance - Austin", url="https://ibm.com/j?jobId=1")
    b = tracker.add(rows, company="IBM", title="Compliance SW Dev Intern: Systems Assurance", url="https://ibm.com/j?jobId=2")
    tracker.update(rows, a["id"], status="Assessment")
    assert a["status"] == "Assessment" and b["status"] == "Found"


def test_save_load_roundtrip_keeps_extra_columns():
    rows = []
    r = tracker.add(rows, company="Acme", title="QA", url="https://x.com/1")
    r["salary"] = "90k"
    tracker.save(rows)
    back = tracker.load()
    assert back[0]["salary"] == "90k" and back[0]["id"] == r["id"]


def _applied(rows, company, n, when="2026-01-01", status="Applied"):
    for i in range(n):
        r = tracker.add(rows, company=company, title=f"Role {i}", url=f"https://{company}.com/{status}/{i}")
        tracker.update(rows, r["id"], status=status, applied=when)


def test_rule_company_cap():
    rows = []
    _applied(rows, "Acme", 3)
    with pytest.raises(rules.RuleViolation, match="limit 3"):
        rules.check("Acme", rows)
    rules.check("Other Co", rows)


def test_rule_one_per_day_and_interviewing_and_skiplist(isolated):
    rows = []
    _applied(rows, "Acme", 1, when=TODAY)
    with pytest.raises(rules.RuleViolation, match="today"):
        rules.check("Acme", rows)
    rows2 = []
    _applied(rows2, "Rocket", 1, status="Interviewing")
    with pytest.raises(rules.RuleViolation, match="interviewing"):
        rules.check("Rocket", rows2)
    cfg = isolated / "config"
    cfg.mkdir()
    (cfg / "settings.json").write_text(json.dumps({"rules": {"skip_companies": ["Evil Corp"]}}))
    with pytest.raises(rules.RuleViolation, match="skip list"):
        rules.check("Evil Corp", [])


def test_queue_done_updates_tracker():
    job = queue.add(company="Acme", title="Validation Engineer", url="https://x.com/9", by="claude")
    assert tracker.load()[0]["status"] == "Queued"
    claimed = queue.next_job("codex")
    assert claimed["id"] == job["id"] and claimed["status"] == "in_progress"
    assert queue.next_job() is None
    queue.finish(job["id"], "applied", "confirmation page seen")
    row = tracker.load()[0]
    assert row["status"] == "Applied" and row["date_applied"] == TODAY and row["follow_up"]
    assert queue.added_today("claude") == 1


def test_queue_add_enforces_rules():
    rows = []
    _applied(rows, "Acme", 3)
    tracker.save(rows)
    with pytest.raises(rules.RuleViolation):
        queue.add(company="Acme", title="Another", url="https://acme.com/new")


def test_cli_smoke(capsys):
    assert cli.main(["add", "--company", "Acme", "--title", "QA", "--url", "https://x.com/q"]) == 0
    assert cli.main(["find", "acme"]) == 0
    assert "Acme" in capsys.readouterr().out
    assert cli.main(["check", "Acme"]) == 0
    assert cli.main(["update", "nope", "--status", "Applied"]) == 1   # clean error, no traceback


def test_profile_and_targets_load_from_settings(isolated):
    from jobos.screen import Profile
    from jobos.targeting import Targets
    cfg = isolated / "config"
    cfg.mkdir()
    (cfg / "settings.json").write_text(json.dumps({
        "profile": {"max_years": 1, "us_citizen": True},
        "targets": {"roles": ["business analyst"], "locations": ["Tampa, FL"]}}))
    p = Profile.load(max_years=None, us_citizen=None, include_internships=True)
    assert p.max_years == 1 and p.us_citizen and p.include_internships
    assert Profile.load(max_years=3).max_years == 3            # CLI flag wins
    assert Targets.load().locations == ["Tampa, FL"]


def test_init_wizard_writes_settings_and_reuses_them(isolated):
    from jobos import wizard
    from jobos.screen import Profile
    from jobos.targeting import Targets
    answers = iter(["business analyst, data analyst", "", "Tampa, FL; Orlando, FL", "10", "Tampa, FL",
                    "y", "", "", "1", "y", "n", "n", "2"])
    wizard.run(ask=lambda _: next(answers), say=lambda _: None)
    t = Targets.load()
    assert t.roles == ["business analyst", "data analyst"] and t.locations == ["Tampa, FL", "Orlando, FL"]
    assert t.radius_miles == 10 and t.center and abs(t.center[0] - 27.97) < 0.05     # offline city lookup
    assert t.exclude_titles == ["sales", "recruiter"] and t.countries == ["United States"]
    assert Profile.load().max_years == 1 and Profile.load().us_citizen
    wizard.run(ask=lambda _: "", say=lambda _: None)        # all Enter: nothing changes
    assert Targets.load().locations == ["Tampa, FL", "Orlando, FL"]
    assert Targets.load().center == t.center and Targets.load().radius_miles == 10
    assert json.loads((isolated / "config" / "settings.json").read_text())["rules"]["max_per_company"] == 2
