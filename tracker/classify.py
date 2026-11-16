"""Tag opportunities with countries, themes, kind; compute relevance + status."""
from __future__ import annotations

import re
from datetime import date, timedelta
from functools import lru_cache

from .models import Opportunity
from .utils import find_deadline, find_open_date, load_yaml, today


def _term_rx(term: str) -> re.Pattern:
    # Short ALL-CAPS acronyms (AI, SME, DPI, RFP) are matched case-sensitively
    # so "ai" inside normal words / "Thai" doesn't count.
    flags = 0 if (term.isupper() and len(term) <= 5) else re.I
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", flags)


@lru_cache(maxsize=1)
def taxonomy() -> dict:
    t = load_yaml("config/taxonomy.yaml") or {}
    compiled = {
        "settings": t.get("settings", {}),
        "weights": t.get("weights", {}),
        "countries": {c: [_term_rx(a) for a in aliases] for c, aliases in t.get("countries", {}).items()},
        "region": [_term_rx(a) for a in t.get("region_terms", [])],
        "themes": {th: [_term_rx(k) for k in kws] for th, kws in t.get("themes", {}).items()},
        "kinds": {k: [_term_rx(x) for x in kws] for k, kws in t.get("opportunity_terms", {}).items()},
    }
    return compiled


def setting(name: str, default=None):
    return taxonomy()["settings"].get(name, default)


def _hits(patterns, text) -> int:
    return sum(1 for p in patterns if p.search(text))


def classify(opp: Opportunity, region_hint: str | None = None) -> Opportunity:
    tx = taxonomy()
    w = tx["weights"]
    text = f"{opp.title} \n {opp.summary} \n {opp.eligibility} \n {opp.requirements} \n {opp.funder}"

    # Countries
    if not opp.countries:
        opp.countries = [c for c, pats in tx["countries"].items() if _hits(pats, text)]
    region_match = bool(region_hint) or _hits(tx["region"], text) > 0
    if not opp.countries and region_match:
        opp.countries = ["ASEAN-wide"]

    # Themes (ordered by number of keyword hits)
    if not opp.themes:
        scored = [(th, _hits(pats, text)) for th, pats in tx["themes"].items()]
        opp.themes = [th for th, n in sorted(scored, key=lambda x: -x[1]) if n > 0]

    # Kind (only refine generic kinds; keep 'lead' & 'tender' from source)
    if opp.kind in ("", "grant", "cfp", "fund"):
        best = max(((k, _hits(p, text)) for k, p in tx["kinds"].items()), key=lambda x: x[1], default=(None, 0))
        if best[1] > 0 and not opp.kind:
            opp.kind = best[0]

    # Dates from free text if the source didn't give them
    if not opp.deadline:
        opp.deadline = find_deadline(text)
    if not opp.open_date:
        opp.open_date = find_open_date(text)

    # Relevance score
    score = 0
    if opp.countries:
        score += w.get("country_or_region", 35)
    if opp.themes:
        score += w.get("theme_first", 30)
        score += min(w.get("theme_extra", 5) * (len(opp.themes) - 1), w.get("theme_extra_cap", 15))
    if any(_hits(p, text) for p in tx["kinds"].values()):
        score += w.get("opportunity_term", 15)
    if opp.deadline:
        score += w.get("has_deadline", 5)
    opp.score = min(score, 100)

    opp.status = compute_status(opp)
    return opp


def compute_status(opp: Opportunity, ref: date | None = None) -> str:
    ref = ref or today()
    raw = (opp.raw_status or "").lower()
    if any(x in raw for x in ("closed", "archived", "cancel", "award")):
        return "closed"
    soon = timedelta(days=int(setting("closing_soon_days", 21)))
    if opp.open_date and date.fromisoformat(opp.open_date) > ref:
        return "forthcoming"
    if "forecast" in raw or "forthcoming" in raw:
        return "forthcoming"
    if opp.deadline:
        dl = date.fromisoformat(opp.deadline)
        if dl < ref:
            return "closed"
        if dl - ref <= soon:
            return "closing_soon"
        return "open"
    if "open" in raw or "posted" in raw or "active" in raw:
        return "open"
    return "unknown"
