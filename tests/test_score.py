"""Fit score: ranks jobs that pass screening, so the top few really are the best."""
from jobos.adapters.base import Posting
from jobos.score import score
from jobos.screen import Profile, screen
from jobos.targeting import Targets

ME = Profile(max_years=1, us_citizen=True)
T = Targets(roles=["data analyst", "business analyst"], locations=["Tampa, FL"], remote=True)


def S(title, text, location="Tampa, FL"):
    p = Posting("Acme", title, "https://x.com/1", location, text=text)
    return score(p, screen(p, ME), ME, T)


def test_great_fit_beats_ok_fit():
    great = S("Data Analyst I", "Requirements\nBachelor's degree. Recent graduates welcome. 0-1 years of experience.")
    ok = S("Reporting Analyst", "Requirements\n1+ years of experience with Excel.", location="Remote - US")
    assert great.total >= 4.5 and great.parts["role"] == 5 and great.parts["experience"] == 5
    assert ok.parts["role"] == 1 and ok.total < great.total                  # "analyst" alone isn't a match
    assert any("recent graduate" in r for r in great.reasons)


def test_stretch_and_flags_lower_the_score():
    stretch = S("Business Analyst", "Requirements\n1 year of experience. Ability to obtain a Secret clearance.")
    assert stretch.parts["experience"] == 3 and stretch.parts["flags"] == 4
    assert stretch.total < S("Business Analyst", "Requirements\nBachelor's degree.").total


def test_failing_screen_scores_one():
    s = S("Senior Data Analyst", "Requirements\n5+ years of experience")
    assert s.total == 1.0 and "fails screening" in s.reasons[0]


def test_title_only_mode_is_not_penalized_as_a_flag():
    s = S("Data Analyst", "")
    assert s.parts["flags"] == 5
