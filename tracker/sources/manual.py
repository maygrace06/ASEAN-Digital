"""Hand-curated opportunities from data/manual.yaml."""
from __future__ import annotations

from ..utils import load_yaml, to_iso
from .base import Source, register

FIELDS = ("title", "url", "funder", "kind", "summary", "countries", "themes", "funding",
          "eligibility", "requirements", "reference", "recurring", "notes")


@register("manual")
class ManualSource(Source):
    def fetch(self):
        rows = load_yaml(self.cfg.get("path", "data/manual.yaml")) or []
        out = []
        for r in rows:
            if not r or not r.get("title"):
                continue
            kw = {k: r[k] for k in FIELDS if r.get(k) not in (None, "")}
            for k in ("eligibility", "requirements", "summary", "notes"):
                if k in kw:
                    kw[k] = " ".join(str(kw[k]).split())
            kw.setdefault("url", "")
            kw["deadline"] = to_iso(r.get("deadline"))
            kw["open_date"] = to_iso(r.get("open_date"))
            out.append(self.make(**kw))
        return out
