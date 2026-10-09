"""Targeting: does the user WANT this job (title, place, language)?"""
from jobos.targeting import Targets, location_ok, text_ok, title_ok

# A Tampa business/IS new grad, not an engineer: the tool must work for them too.
TAMPA = Targets(roles=["business analyst", "data analyst", "it analyst", "systems analyst"],
                exclude_titles=["senior", "sales"], locations=["Tampa, FL"], remote=True)
ENG = Targets(roles=["test engineer", "firmware", "validation"], locations=["Austin, TX"],
              countries=["United States", "Japan"])


def test_title_roles_and_excludes():
    assert title_ok("Business Analyst I", TAMPA).ok
    assert title_ok("IT Analyst - New Grad", TAMPA).ok
    assert not title_ok("Senior Business Analyst", TAMPA).ok
    assert not title_ok("Inside Sales Representative", TAMPA).ok
    assert not title_ok("Firmware Engineer", TAMPA).ok
    assert title_ok("Anything", Targets()).ok                 # no roles set = no title filter


def test_location_city_remote_country():
    assert location_ok("Tampa, FL", TAMPA).ok
    assert location_ok("Remote - US", TAMPA).ok
    assert not location_ok("Chicago, IL", TAMPA).ok
    assert not location_ok("Remote", Targets(remote=False, locations=["Tampa, FL"])).ok
    assert location_ok("Tokyo, Japan", ENG).ok              # opted into Japan
    assert not location_ok("Berlin, Germany", ENG).ok
    assert location_ok("Denver, CO", Targets()).ok           # no cities: any US location
    assert not location_ok("London, UK", Targets()).ok


def test_language_and_visa():
    assert not text_ok("Business-level Japanese required (JLPT N2).", "Tokyo, Japan", ENG).ok
    assert text_ok("Fluent Japanese is a plus", "Tokyo, Japan", Targets(languages=["English", "Japanese"])).ok
    m = text_ok("English-speaking team.", "Tokyo, Japan", ENG)
    assert m.ok and any("visa" in w for w in m.why)
    assert not text_ok("We offer visa sponsorship.", "Tokyo, Japan", ENG).why
    assert text_ok("Spanish is nice to have", "Austin, TX", ENG).ok


# Radius targeting: within 10 miles of Raymond James Stadium, Tampa (a public landmark).
TAMPA_RADIUS = Targets(roles=["business analyst"], center=[27.976, -82.503], radius_miles=10, remote=False)


def test_geo_lookup_and_distance():
    from jobos.geo import geocode, haversine_miles, lookup
    tampa = lookup("Tampa", "FL")
    assert tampa and abs(tampa[0] - 27.97) < 0.05
    assert lookup("Tampa", "Florida") == tampa
    assert lookup("Tampa", "KS") != tampa                    # same name, other state
    assert lookup("St Petersburg", "FL") and lookup("Saint Petersburg", "FL") == lookup("St. Petersburg", "FL")
    assert lookup("West Palm Beach", "FL")                   # "st" inside a word is not "St."
    assert lookup("Nashville", "TN")                         # consolidated city ("Nashville-Davidson")
    assert lookup("Atlantis", "ZZ") is None and lookup("Nowhereville", "FL") is None
    assert geocode("Tampa, Florida, United States") == tampa
    assert 80 < haversine_miles(tampa, lookup("Orlando", "FL")) < 90


def test_location_radius():
    assert location_ok("Tampa, FL", TAMPA_RADIUS).ok
    assert location_ok("Temple Terrace, FL", TAMPA_RADIUS).ok      # ~9 mi
    assert location_ok("Town 'n' Country, Florida, United States", TAMPA_RADIUS).ok
    assert not location_ok("Brandon, FL", TAMPA_RADIUS).ok          # ~13 mi
    assert not location_ok("Orlando, FL", TAMPA_RADIUS).ok
    assert not location_ok("St. Petersburg, FL", TAMPA_RADIUS).ok   # ~17 mi
    # Greenhouse multi-location: in if any segment is in range
    m = location_ok("Orlando, FL; Tampa, FL", TAMPA_RADIUS)
    assert m.ok and "mi away" in m.why[0]
    # radius plus an explicit city list: either one qualifies
    both = Targets(center=[27.976, -82.503], radius_miles=10, locations=["Austin, TX"])
    assert location_ok("Austin, TX", both).ok and location_ok("Tampa, FL", both).ok
    assert not location_ok("Orlando, FL", both).ok
    # unknown place falls back to the old rules (US-only when no city list)
    assert location_ok("Some Office Park, FL", TAMPA_RADIUS).ok


def test_radius_loads_from_settings_shape():
    t = Targets(**{"radius_miles": 10, "center": [27.976, -82.503], "roles": []})
    assert t.radius_miles == 10 and t.center == [27.976, -82.503]


def test_locate_home_offline():
    from jobos.geo import locate_home
    assert locate_home("27.976, -82.503", online=False)[0] == (27.976, -82.503)
    p, how = locate_home("Main St & 1st Ave, Tampa, FL", online=False)
    assert p and "Tampa" in how                                 # falls back to the city
    assert locate_home("nowhere at all", online=False)[0] is None


def test_related_titles():
    from jobos.titles import related
    ba = related(["Business Analyst"])
    assert "operations analyst" in ba and "business analyst" not in ba
    mixed = related(["test engineer", "firmware"])
    assert "qa engineer" in mixed and "firmware engineer" in mixed      # every role gets suggestions
    assert related(["basket weaver"]) == []
