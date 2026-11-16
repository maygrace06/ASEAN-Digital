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
        "focus": {g: set(ths) for g, ths in (t.get("focus") or {}).items()},
        "advisory": [_term_rx(x) for x in t.get("advisory_terms", [])],
        "off_scope": [_term_rx(x) for x in t.get("off_scope_terms", [])],
        "weak": {w.lower() for w in t.get("weak_terms", [])},
        "theme_terms": {th: list(kws) for th, kws in t.get("themes", {}).items()},
        "advisory_terms": list(t.get("advisory_terms", [])),
        "off_scope_terms": list(t.get("off_scope_terms", [])),
    }
    return compiled


def _matched(terms, patterns, text) -> list[str]:
    return [t for t, p in zip(terms, patterns) if p.search(text)]


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

    opp.score, opp.score_why = score(opp, text)
    opp.status = compute_status(opp)
    return opp


def score(opp: Opportunity, text: str) -> tuple[int, str]:
    """Relevance 0-100 for: ASEAN · (1) digital economy · (2) workforce planning ·
    consulting work or funding calls. Returns (score, explanation)."""
    tx = taxonomy()
    w = tx["weights"]
    pts, why = 0, []

    def add(n, label):
        nonlocal pts
        pts += n
        why.append(f"{label} {'+' if n >= 0 else '−'}{abs(n)}")

    if opp.countries:
        add(w.get("country_or_region", 25), f"ASEAN ({', '.join(opp.countries[:3])})")

    # Focus themes: only strong (non-weak) terms earn focus points
    strong = {}
    for th in opp.themes:
        terms = _matched(tx["theme_terms"][th], tx["themes"][th], text)
        terms = [t for t in terms if t.lower() not in tx["weak"]]
        if terms:
            strong[th] = terms
    groups = tx["focus"]
    prim = {th: t for th, t in strong.items() if th in groups.get("primary", set())}
    sec = {th: t for th, t in strong.items() if th in groups.get("secondary", set())}
    if prim:
        add(w.get("focus_primary", 35), "Digital economy: " + ", ".join(sorted({x for v in prim.values() for x in v})[:4]))
    elif sec:
        add(w.get("focus_secondary", 30), "Workforce: " + ", ".join(sorted({x for v in sec.values() for x in v})[:4]))
    elif opp.themes:
        add(w.get("focus_other", 10), "Other theme: " + ", ".join(opp.themes[:2]))
    if prim and sec:  # both focus areas: small bonus
        add(5, "Workforce too: " + ", ".join(sorted({x for v in sec.values() for x in v})[:3]))
    focus_terms = {x for v in {**prim, **sec}.values() for x in v}
    title_rx = [_term_rx(t) for t in focus_terms]
    if any(p.search(opp.title) for p in title_rx):
        add(w.get("focus_in_title", 10), "focus topic in title")

    # Type of work: consulting/advisory or formal call beats generic funding words
    adv = _matched(tx["advisory_terms"], tx["advisory"], text)
    fund_kinds = ("grant", "fund", "fellowship", "accelerator")
    funding = [k for k in fund_kinds if _hits(tx["kinds"].get(k, []), text)]
    if opp.kind == "lead":
        # News articles: "funding round", "invests" are not calls. Only a real
        # call / grant / RFP mentioned in the article counts.
        funding = [k for k in ("grant",) if _hits(tx["kinds"].get(k, []), text)]
        adv = [] if not _hits(tx["kinds"].get("cfp", []), text) else adv
    if adv or _hits(tx["kinds"].get("cfp", []), text):
        add(w.get("advisory_work", 20), "Consulting/call: " + ", ".join(adv[:3] or ["call"]))
    elif funding:
        add(w.get("funding_call", 15), "Funding: " + ", ".join(funding))
    elif opp.kind == "lead":
        add(-w.get("news_no_call_penalty", 20), "News, no call/grant mentioned")

    if opp.deadline:
        add(w.get("has_deadline", 5), "has deadline")

    off = _matched(tx["off_scope_terms"], tx["off_scope"], opp.title)
    if off:
        add(-w.get("off_scope_penalty", 40), "Out of scope: " + ", ".join(off[:3]))

    return max(0, min(pts, 100)), " · ".join(why)


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
