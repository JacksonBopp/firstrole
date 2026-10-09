"""Related job titles. New grads often don't know every name a job goes by, so searching only
"business analyst" misses "operations analyst" and "systems analyst". These families are
hand-picked entry-level titles that ask for similar skills. Add to them freely.
"""
from __future__ import annotations

import re

FAMILIES = [
    ["business analyst", "data analyst", "operations analyst", "business intelligence analyst", "reporting analyst",
     "systems analyst", "product analyst", "business systems analyst", "supply chain analyst"],
    ["data analyst", "data engineer", "analytics engineer", "business intelligence developer", "data scientist"],
    ["it analyst", "it support specialist", "help desk technician", "desktop support technician",
     "systems administrator", "technical support engineer", "network technician", "systems analyst"],
    ["test engineer", "qa engineer", "quality engineer", "validation engineer", "verification engineer",
     "software engineer in test", "test automation engineer", "hardware test engineer", "reliability engineer"],
    ["firmware engineer", "embedded software engineer", "embedded systems engineer", "embedded engineer",
     "device driver engineer", "hardware validation engineer"],
    ["hardware engineer", "electrical engineer", "fpga engineer", "asic verification engineer",
     "hardware test engineer", "hardware validation engineer"],
    ["software engineer", "software developer", "application developer", "backend developer",
     "full stack developer", "software engineer in test"],
    ["automation engineer", "controls engineer", "manufacturing engineer", "process engineer",
     "robotics engineer", "manufacturing test engineer", "test engineer"],
    ["ai engineer", "machine learning engineer", "solutions engineer", "forward deployed engineer",
     "customer engineer", "implementation engineer", "technical consultant"],
    ["project coordinator", "associate project manager", "program coordinator", "operations coordinator",
     "business operations associate"],
    ["associate product manager", "product analyst", "product operations associate", "business analyst"],
    ["associate consultant", "technology consultant", "implementation consultant", "business analyst"],
    ["financial analyst", "accounting analyst", "fp&a analyst", "staff accountant", "business analyst"],
    ["marketing analyst", "digital marketing specialist", "marketing coordinator", "data analyst"],
]


def _norm(s: str) -> str:
    return " ".join(re.findall(r"[a-z0-9&+#]+", s.lower()))


def related(roles: list[str], limit: int = 8) -> list[str]:
    """Titles from the same families as `roles`, closest families first, excluding the roles themselves."""
    have = {_norm(r) for r in roles}
    per_role = []
    for r in roles:
        mine: list[str] = []
        for fam in FAMILIES:
            if any(_norm(r) == t or _norm(r) in t or t in _norm(r) for t in fam):
                mine += [t for t in fam if t not in have and t not in mine]
        per_role.append(mine)
    out: list[str] = []
    for i in range(max(map(len, per_role), default=0)):             # take turns, so every role gets some
        out += [m[i] for m in per_role if i < len(m) and m[i] not in out]
    return out[:limit]
