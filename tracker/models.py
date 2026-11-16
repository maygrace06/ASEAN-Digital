"""Data model for a funding opportunity."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Opportunity:
    title: str
    url: str
    source: str                       # source id
    kind: str = "grant"               # grant | cfp | tender | fund | fellowship | accelerator | lead
    funder: str = ""
    summary: str = ""
    countries: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    open_date: Optional[str] = None   # ISO YYYY-MM-DD
    deadline: Optional[str] = None    # ISO YYYY-MM-DD
    funding: str = ""
    eligibility: str = ""
    requirements: str = ""
    reference: str = ""               # official number (NOFO, bid ref, call id)
    recurring: str = ""
    notes: str = ""
    # computed / bookkeeping
    id: str = ""
    status: str = "unknown"           # forthcoming | open | closing_soon | closed | unknown
    score: int = 0
    first_seen: str = ""
    last_seen: str = ""
    raw_status: str = ""              # status text as given by the source

    def __post_init__(self):
        if not self.id:
            self.id = make_id(self.url or self.title, self.reference)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Opportunity":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def make_id(url: str, reference: str = "") -> str:
    key = (reference or url).strip().lower().rstrip("/")
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
