"""Screening cases taken from real postings (paraphrased) that a human had to judge by hand."""
from jobos.adapters.base import Posting
from jobos.screen import Profile, required_years, screen

ME = Profile(max_years=2, us_citizen=True)


def P(title, text, is_open=True):
    return Posting(company="X", title=title, url="https://x.com/1", text=text, is_open=is_open)


def test_preferred_years_do_not_count():
    text = """Requirements
Bachelor's degree in Computer Science, Data Science, or related field
Strong Python programming skills
Preferred Education and Experience
2-5 years of experience in machine learning or related field."""
    v = screen(P("Associate Machine Learning Engineer", text), ME)
    assert v.ok and v.required_years is None


def test_required_years_reject():
    text = "BASIC QUALIFICATIONS\n- 3+ years of non-internship professional software development experience\n"
    v = screen(P("Embedded Software Engineer", text), ME)
    assert not v.ok and v.required_years == 3


def test_zero_to_two_years_is_fine_and_signals_entry():
    text = "What we're looking for\n0 to 3 years of software engineering experience. Recent graduates are encouraged to apply."
    v = screen(P("Forward Deployed Engineer", text), Profile(max_years=3, us_citizen=True))
    assert v.ok and v.required_years == 0
    assert any("recent graduates" in s for s in v.signals)


def test_company_history_years_ignored():
    assert required_years("For more than 55 years, Analog Devices has been inventing new technologies.") is None
    assert required_years("Requirements\nFor over 25 years of experience serving customers, we lead.") is None
    assert required_years("About us: our founders bring 100 years of experience.") is None


def test_age_requirement_is_not_experience():
    assert required_years("Requirements\nMust be 18 years of age or older.") is None
    assert required_years("Requirements\nApplicants must be at least 21 years old.") is None


def test_common_phrasings_still_detected():
    assert required_years("Requirements\nMinimum of 4 years of relevant experience") == 4
    assert required_years("Requirements\nAt least 2 years experience with C") == 2
    assert required_years("Requirements\n5+ yrs professional software development") == 5


def test_senior_title_and_intern_title():
    assert not screen(P("Senior Test Engineer", "x"), ME).ok
    assert not screen(P("Software Engineer II", "x"), ME).ok
    assert not screen(P("Firmware Engineering Intern", "x"), ME).ok
    assert screen(P("Firmware Engineering Intern", "x"), Profile(include_internships=True, us_citizen=True)).ok


def test_clearance_active_vs_obtain():
    active = "Required Qualifications\nMust have an active Secret security clearance."
    obtain = "Required Qualifications\nAbility to obtain and maintain a Secret clearance."
    assert not screen(P("Test Engineer", active), ME).ok
    v = screen(P("Test Engineer", obtain), ME)
    assert v.ok and any("obtain" in f for f in v.flags)
    assert not screen(P("Test Engineer", obtain), Profile(us_citizen=False)).ok


def test_prior_internship_required():
    text = "Required Qualifications:\nBachelor's degree obtained between May 2026 and June 2027\nPrior Co-Op or internship experience"
    v = screen(P("Systems Test Engineer, Rotational Program", text), ME)
    assert not v.ok and any("internship" in r for r in v.reasons)
    assert any("graduation" in f for f in v.flags)


def test_closed_posting():
    assert not screen(P("Test Engineer", "x", is_open=False), ME).ok


def test_masters_required():
    assert not screen(P("Design Engineer", "Requirements\nMaster's degree in EE required."), ME).ok
    assert screen(P("Design Engineer", "Requirements\nBachelor's or Master's degree in EE."), ME).ok


def test_spelled_out_years():
    assert required_years("Requirements\nThree (3) years of experience in test automation") == 3
    assert required_years("Requirements\ntwo+ years of hands-on Python experience") == 2
    assert required_years("Requirements\nFive years experience with C") == 5
    assert required_years("Requirements\nFive or more years of experience in SQL") == 5
