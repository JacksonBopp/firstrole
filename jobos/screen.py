"""Rule-based screening: read the FULL posting and decide if it's a realistic fit.

No AI needed. It separates *required* from *preferred* sections, because "2-5 years
preferred" is fine for a new grad while "3+ years required" is not.

    from jobos.screen import Profile, screen
    v = screen(posting, Profile(max_years=2, us_citizen=True))
    v.ok, v.reasons, v.flags, v.signals, v.required_years
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SENIOR_TITLE = re.compile(r"\b(senior|sr\.?|staff|principal|lead|manager|director|head of|vp|architect|"
                          r"distinguished|fellow)\b|\b(II|III|IV|2|3)\s*$", re.I)
INTERN_TITLE = re.compile(r"\b(intern|internship|co-?op)\b", re.I)
PREFERRED_HEAD = re.compile(r"(?i)\b(preferred|nice to have|bonus|a plus|desired|ideal(ly)?|plus points?|would be great)\b")
REQUIRED_HEAD = re.compile(r"(?i)\b(required|requirements|minimum|basic qualifications|must have|what you.ll need|"
                           r"what you need|you have|qualifications|who you are)\b")
# "3+ years of experience", "2-5 years professional", "minimum of 1 year relevant". Guards:
#  - (?<![\d.]) so "100 years" never matches as "00 years"
#  - not followed by "of age" / "old" ("must be 18 years of age")
#  - must be followed by an experience word, not just "of" ("25 years of serving customers")
YEARS = re.compile(r"(?i)(?<![\d.])(\d{1,2})\s*(?:\+|plus|or\s+more|or\s+greater)?\s*(?:(?:-|–|to)\s*(\d{1,2})\s*\+?)?\s*"
                   r"(?:years?|yrs?)\b(?!\s+(?:of\s+age|old))"
                   r"(?=[^.\n]{0,40}\b(?:experience|professional|industry|relevant|hands-on|work history)\b)")
_NUMBER_WORDS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split())}
# "three (3) years", "two+ years", "Five years" -> digits, so YEARS can read them
_SPELLED = re.compile(r"(?i)\b(" + "|".join(_NUMBER_WORDS) + r")\b(\s*\(\s*\d+\s*\))?")


def _numerize(line: str) -> str:
    return _SPELLED.sub(lambda m: _NUMBER_WORDS[m.group(1).lower()], line)


# "for over 25 years ...", "more than 10 years ..." describe the company, not the candidate
HISTORY_LEAD = re.compile(r"(?i)\b(for(?:\s+(?:over|more than|nearly|almost))?|over|more than|nearly|almost)\s*$")
ENTRY_SIGNALS = re.compile(r"(?i)\b(new grad(uate)?s?|recent grad(uate)?s?|entry[- ]level|early[- ]career|university grad|"
                           r"college grad|0\s*(?:-|–|to)\s*[12]\s*years|graduating|campus|rotational program|development program|"
                           r"(?:grads?|graduates) (?:are )?encouraged)\b")
ADVANCED_DEGREE_REQ = re.compile(r"(?i)\b(master'?s|m\.s\.|ms degree|ph\.?d)\b[^.\n]{0,40}\b(required|is required|must)\b")
ACTIVE_CLEARANCE = re.compile(r"(?i)\b(active|current(ly)? (?:hold|possess)|must (?:have|possess|hold))\b[^.\n]{0,40}"
                              r"\b(secret|ts/sci|top secret|security clearance)\b")
OBTAIN_CLEARANCE = re.compile(r"(?i)\b(ability|able|eligible|willing)\b[^.\n]{0,25}\b(obtain|get)\b[^.\n]{0,40}clearance")
CITIZEN_REQ = re.compile(r"(?i)\b(u\.?s\.? citizen(ship)?|us person|green card)\b[^.\n]{0,40}\b(required|must|only)\b|"
                         r"\bmust be a u\.?s\.? citizen\b")
NO_SPONSOR = re.compile(r"(?i)\b(not|unable to|cannot|won.t|will not)\b[^.\n]{0,20}\bsponsor")
INTERNSHIP_REQ = re.compile(r"(?i)\b(prior|previous|completed|at least one)\b[^.\n]{0,25}\b(internship|co-?op)\b[^.\n]{0,30}"
                            r"(experience|required)?")


@dataclass
class Profile:
    max_years: int = 2                 # reject if a REQUIRED section asks for more than this
    us_citizen: bool = False
    needs_sponsorship: bool = False
    has_clearance: bool = False
    has_internship: bool = False
    include_internships: bool = False
    advanced_degree: bool = False
    min_score: float = 3.5             # fit scores below this are "weak fits" (see score.py)

    @classmethod
    def load(cls, **overrides) -> "Profile":
        """settings.json "profile" section, then any non-None overrides (CLI flags)."""
        from . import paths
        cfg = {k: v for k, v in paths.settings("profile").items() if k in cls.__dataclass_fields__}
        cfg.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**cfg)


@dataclass
class Verdict:
    ok: bool
    required_years: int | None = None
    reasons: list[str] = field(default_factory=list)   # hard fails
    flags: list[str] = field(default_factory=list)     # worth a human look
    signals: list[str] = field(default_factory=list)   # good signs

    def summary(self) -> str:
        head = "FIT" if self.ok else "SKIP"
        parts = [head] + [f"x {r}" for r in self.reasons] + [f"! {f}" for f in self.flags] + [f"+ {s}" for s in self.signals]
        return "\n  ".join(parts)


def _sections(text: str) -> list[tuple[str, str]]:
    """Split into (kind, line) where kind is 'preferred', 'required' or 'other'.
    A heading-like line switches the kind for the lines that follow it."""
    kind, out = "other", []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        heading = len(s) < 70 and not s.endswith(".")
        if heading and PREFERRED_HEAD.search(s):
            kind = "preferred"
        elif heading and REQUIRED_HEAD.search(s):
            kind = "required"
        # inline "(preferred)" / "preferred:" on a single bullet
        line_kind = "preferred" if PREFERRED_HEAD.search(s) and kind != "preferred" and not heading else kind
        out.append((line_kind, s))
    return out


def required_years(text: str) -> int | None:
    """Smallest years figure a required (or unlabeled) line asks for, e.g. '3-5 years' -> 3, '0-2 years' -> 0."""
    found = []
    for kind, line in _sections(text):
        if kind == "preferred":
            continue
        line = _numerize(line)
        for m in YEARS.finditer(line):
            if HISTORY_LEAD.search(line[:m.start()]):
                continue                       # "for over 25 years of experience serving customers"
            lo = int(m.group(1))
            if lo <= 20:
                found.append(lo)
    return max(found) if found else None


def screen(posting, profile: Profile | None = None) -> Verdict:
    p = profile or Profile()
    title, text = posting.title or "", posting.text or ""
    v = Verdict(ok=True)

    if not getattr(posting, "is_open", True):
        v.reasons.append("posting is closed")
    if SENIOR_TITLE.search(title):
        v.reasons.append(f"senior-level title: {title!r}")
    if INTERN_TITLE.search(title) and not p.include_internships:
        v.reasons.append("internship / co-op")
    if not text:
        v.flags.append("no description fetched: read the posting before deciding")

    yrs = required_years(text)
    v.required_years = yrs
    if yrs is not None and yrs > p.max_years:
        v.reasons.append(f"requires {yrs}+ years (your limit: {p.max_years})")

    required_lines = " ".join(l for k, l in _sections(text) if k != "preferred")
    if ADVANCED_DEGREE_REQ.search(required_lines) and not p.advanced_degree:
        v.reasons.append("requires a Master's or PhD")
    if ACTIVE_CLEARANCE.search(required_lines) and not p.has_clearance:
        v.reasons.append("requires an ACTIVE security clearance")
    elif OBTAIN_CLEARANCE.search(text):
        (v.flags if p.us_citizen else v.reasons).append("must be able to obtain a security clearance")
    if CITIZEN_REQ.search(text) and not p.us_citizen:
        v.reasons.append("US citizenship / US person required")
    if p.needs_sponsorship and NO_SPONSOR.search(text):
        v.reasons.append("does not sponsor visas")
    if INTERNSHIP_REQ.search(required_lines) and not p.has_internship:
        v.reasons.append("requires prior internship / co-op experience")

    for m in sorted({m.group(0).lower() for m in ENTRY_SIGNALS.finditer(text + " " + title)})[:4]:
        v.signals.append(m)
    if re.search(r"(?i)\b(graduat\w*|degree\s+(?:obtained|completed|conferred|earned))\b[^.\n]{0,30}"
                 r"\b(between|by|in|no later than|before)\s", text):
        v.flags.append("has a graduation-date window: check it matches yours")

    v.ok = not v.reasons
    return v
