"""Adapter parsing, with the boards' JSON faked (shapes copied from real responses). No network."""
import pytest

from jobos import adapters
from jobos.adapters import NotFound, smartrecruiters as sr, workable as wk


def test_detect_new_boards():
    assert adapters.detect("https://jobs.smartrecruiters.com/BoschGroup/744000154516279-test-engineer") is sr
    assert adapters.detect("https://careers.smartrecruiters.com/BoschGroup") is sr
    assert adapters.detect("https://apply.workable.com/huggingface/j/81B46579FE") is wk
    assert adapters.detect("https://acme.workable.com/") is wk


def test_url_parts():
    assert sr._parts("https://jobs.smartrecruiters.com/BoschGroup/744000154516279-software-validation") == \
        ("BoschGroup", "744000154516279")
    assert sr._parts("https://api.smartrecruiters.com/v1/companies/BoschGroup/postings/744000154516279") == \
        ("BoschGroup", "744000154516279")
    assert sr._parts("https://careers.smartrecruiters.com/BoschGroup") == ("BoschGroup", None)
    assert wk._parts("https://apply.workable.com/huggingface/j/81B46579FE/apply") == ("huggingface", "81B46579FE")
    assert wk._parts("https://acme.workable.com/j/ABC123") == ("acme", "ABC123")
    with pytest.raises(ValueError):
        wk._parts("https://apply.workable.com/j/81B46579FE")      # no company in the short link


SR_LIST = {"totalFound": 2, "content": [
    {"id": "1", "name": "Software Validation Engineer", "releasedDate": "2026-10-01T00:00:00Z",
     "location": {"fullLocation": "Owatonna, MN, United States", "remote": False}},
    {"id": "2", "name": "Embedded Test Engineer Intern", "location": {"city": "Ho Chi Minh", "region": "",
                                                                     "country": "vn", "remote": True}}]}
SR_DETAIL = {"id": "1", "name": "Software Validation Engineer", "active": True,
             "company": {"name": "Bosch Group"}, "postingUrl": "https://jobs.smartrecruiters.com/BoschGroup/1-x",
             "location": {"fullLocation": "Owatonna, MN, United States"}, "experienceLevel": {"label": "Entry Level"},
             "jobAd": {"sections": {"jobDescription": {"title": "Job Description", "text": "<p>Test things.</p>"},
                                    "qualifications": {"title": "Qualifications", "text": "<ul><li>BS in CompE</li></ul>"},
                                    "videos": {"title": "Videos", "text": ""}}}}


def test_smartrecruiters(monkeypatch):
    monkeypatch.setattr(sr, "http_json", lambda url, **kw: SR_DETAIL if url.endswith("/1") else SR_LIST)
    jobs = sr.list_postings("https://careers.smartrecruiters.com/BoschGroup")
    assert [p.location for p in jobs] == ["Owatonna, MN, United States", "Ho Chi Minh, vn (Remote)"]
    assert [p.title for p in sr.list_postings("https://careers.smartrecruiters.com/BoschGroup", "validation")] == \
        ["Software Validation Engineer"]
    p = sr.fetch_posting(jobs[0].url)
    assert p.company == "Bosch Group" and p.is_open and p.extra["level"] == "Entry Level"
    assert "Qualifications\nBS in CompE" in p.text


def test_smartrecruiters_unknown_company_and_closed(monkeypatch):
    monkeypatch.setattr(sr, "http_json", lambda url, **kw: {"totalFound": 0, "content": []})
    with pytest.raises(NotFound):
        sr.list_postings("https://careers.smartrecruiters.com/NoSuchCo")

    def gone(url, **kw):
        raise NotFound(url)
    monkeypatch.setattr(sr, "http_json", gone)
    assert not sr.fetch_posting("https://jobs.smartrecruiters.com/BoschGroup/123456789").is_open


WK_BOARD = {"name": "Hugging Face", "jobs": [
    {"title": "ML Engineer", "shortcode": "AB12", "telecommuting": True, "published_on": "2026-05-29",
     "locations": [{"country": "France", "city": "Paris", "region": "Île-de-France"}],
     "description": "<p>Requirements</p><ul><li>2+ years of Python experience</li></ul>"}]}
WK_JOB = {"title": "ML Engineer", "state": "published", "remote": False, "published": "2026-05-29T00:00:00Z",
          "location": {"city": "Austin", "region": "Texas", "country": "United States"},
          "description": "<p>Build.</p>", "requirements": "<p>BS degree</p>", "benefits": ""}


def test_workable(monkeypatch):
    monkeypatch.setattr(wk, "http_json", lambda url, **kw: WK_JOB if "/v2/" in url else WK_BOARD)
    [p] = wk.list_postings("https://apply.workable.com/huggingface/")
    assert p.company == "Hugging Face" and p.location == "Paris, Île-de-France, France (Remote)"
    assert "2+ years of Python" in p.text and p.url.endswith("/huggingface/j/AB12")
    d = wk.fetch_posting(p.url)
    assert d.location == "Austin, Texas, United States" and "BS degree" in d.text and d.is_open


# Trimmed from real logged-out LinkedIn responses.
LI_CARD = """<li><div class="base-card" data-entity-urn="urn:li:jobPosting:{id}">
<h3 class="base-search-card__title">  {title}  </h3>
<h4 class="base-search-card__subtitle"><a href="#">  Acme &amp; Co  </a></h4>
<span class="job-search-card__location">  Austin, TX  </span>
<time class="job-search-card__listdate" datetime="2026-10-07">1 day ago</time></div></li>"""
LI_JOB = """<h2 class="top-card-layout__title">SQA Test Engineer</h2>
<a class="topcard__org-name-link" href="#">  HP  </a>
<span class="topcard__flavor topcard__flavor--bullet">  Austin, TX  </span>
<div class="show-more-less-html__markup">Requirements<br>2+ years of test experience</div>
<h3 class="description__job-criteria-subheader">Seniority level</h3>
<span class="description__job-criteria-text">  Entry level  </span>"""


def test_linkedin_search_and_posting(monkeypatch):
    from jobos.adapters import linkedin as li
    monkeypatch.setattr(li, "PAUSE", 0)
    calls = []

    def fake(path, params=None):
        calls.append(params)
        if path.startswith("jobPosting/"):
            return LI_JOB
        start = params["start"]
        return "<ul>" + "".join(LI_CARD.format(id=start + i, title=f"Test Engineer {start + i}")
                                for i in range(10 if start == 0 else 3)) + "</ul>"
    monkeypatch.setattr(li, "_get", fake)
    url = "https://www.linkedin.com/jobs/search/?keywords=test%20engineer&location=Austin&f_E=2&f_TPR=r604800"
    jobs = li.list_postings(url)
    assert len(jobs) == 13 and len(calls) == 2                 # stops at a short page
    assert "f_E" not in calls[0] and calls[0]["f_TPR"] == "r604800"
    assert (jobs[0].company, jobs[0].location, jobs[0].posted) == ("Acme & Co", "Austin, TX", "2026-10-07")
    assert jobs[0].url == "https://www.linkedin.com/jobs/view/0"
    p = li.fetch_posting("https://www.linkedin.com/jobs/view/sqa-test-engineer-at-hp-4475166287?trk=x")
    assert (p.title, p.company, p.location) == ("SQA Test Engineer", "HP", "Austin, TX")
    assert "2+ years" in p.text and p.extra["seniority level"] == "Entry level" and p.is_open
    assert li._job_id("https://www.linkedin.com/jobs/search/?currentJobId=42&keywords=x") == "42"
    with pytest.raises(ValueError):
        li.list_postings("https://www.linkedin.com/jobs/search/?location=Austin")    # no keywords


def test_linkedin_company_slugs():
    from jobos.adapters.linkedin import _same_title, _slugs
    assert _slugs("Tata Consultancy Services, Inc.") == ["tataconsultancyservices", "tata-consultancy-services"]
    assert _slugs("Scale AI") == ["scaleai", "scale-ai"]
    assert _same_title("Test Engineer I", "test engineer i") and not _same_title("QA", "QA Lead")
