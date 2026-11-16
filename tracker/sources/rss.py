"""Generic RSS / Atom feeds (one or many URLs per source)."""
from __future__ import annotations

import feedparser

from ..utils import clean_text, get, to_iso
from .base import Source, register


@register("rss")
class RssSource(Source):
    def fetch(self):
        urls = self.cfg.get("urls") or [self.cfg["url"]]
        out = []
        for url in urls:
            try:
                feed = feedparser.parse(get(url).content)
            except Exception as e:  # keep going with other URLs
                self.warn(url, e)
                continue
            for e in feed.entries:
                summary = clean_text(e.get("summary") or e.get("description") or "")
                opp = self.make(
                    title=clean_text(e.get("title", ""), 300),
                    url=e.get("link", ""),
                    summary=summary,
                    open_date=to_iso(e.get("published") or e.get("updated")) if self.kind != "lead" else None,
                    funder=self.funder,
                )
                publisher = (e.get("source") or {}).get("title", "") if isinstance(e.get("source"), dict) else ""
                if self.kind == "lead":
                    opp.notes = (f"News lead ({publisher or 'news'}) published "
                                 f"{to_iso(e.get('published')) or '?'} — verify on the official site.")
                    opp.open_date = None
                if opp.title and opp.url and self.keep(opp):
                    out.append(opp)
        return out
