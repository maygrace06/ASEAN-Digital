"""Generic HTML list pages, configured with CSS selectors in sources.yaml.

Config keys:
  url, item_selector, link_selector (default "a"), title_selector (optional),
  deadline_selector (optional), summary_selector (optional),
  context_parent_levels (int, read text from N parents up for dates),
  skip_if_text (string: skip items whose context contains it)
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..utils import clean_text, find_deadline, find_open_date, get, to_iso
from .base import Source, register


@register("html")
class HtmlSource(Source):
    def fetch(self):
        c = self.cfg
        page = get(c["url"]).text
        soup = BeautifulSoup(page, "html.parser")
        out, seen = [], set()
        for item in soup.select(c["item_selector"]):
            link_el = item if item.name == "a" else item.select_one(c.get("link_selector", "a"))
            if not link_el or not link_el.get("href"):
                continue
            url = urljoin(c["url"], link_el["href"])
            if url in seen:
                continue
            seen.add(url)
            title_el = item.select_one(c["title_selector"]) if c.get("title_selector") else link_el
            title = clean_text(title_el.get_text(" ") if title_el else "", 300)

            ctx = item
            for _ in range(int(c.get("context_parent_levels", 0))):
                if ctx.parent is not None:
                    ctx = ctx.parent
            ctx_text = clean_text(ctx.get_text(" "), 3000)
            if c.get("skip_if_text") and c["skip_if_text"].lower() in ctx_text.lower():
                continue

            deadline = None
            if c.get("deadline_selector"):
                d = ctx.select_one(c["deadline_selector"])
                deadline = to_iso(d.get_text(" ")) if d else None
            deadline = deadline or find_deadline(ctx_text)
            summary = ""
            if c.get("summary_selector"):
                s = ctx.select_one(c["summary_selector"])
                summary = clean_text(s.get_text(" ")) if s else ""
            opp = self.make(title=title, url=url, summary=summary or ctx_text[:600],
                            deadline=deadline, open_date=find_open_date(ctx_text))
            if title and self.keep(opp):
                out.append(opp)
        return out
