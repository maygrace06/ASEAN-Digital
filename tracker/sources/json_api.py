"""Generic JSON API source — map any JSON endpoint with dotted paths.

Config keys: url, method (GET|POST), params, body (JSON for POST), headers,
items_path, fields: {title, url, deadline, open_date, summary, funder,
reference, funding, countries, status}
"""
from __future__ import annotations

from ..utils import clean_text, dig, get, post, to_iso
from .base import Source, register


@register("json_api")
class JsonApiSource(Source):
    def fetch(self):
        c = self.cfg
        kw = {"params": c.get("params"), "headers": c.get("headers")}
        if c.get("method", "GET").upper() == "POST":
            data = post(c["url"], json=c.get("body"), **kw).json()
        else:
            data = get(c["url"], **kw).json()
        items = dig(data, c.get("items_path", "")) or []
        f = c.get("fields", {})
        out = []
        for it in items:
            val = lambda k: dig(it, f[k]) if f.get(k) else None  # noqa: E731
            url = val("url") or ""
            if c.get("url_template") and not url:
                url = c["url_template"].format(**it)
            countries = val("countries")
            opp = self.make(
                title=clean_text(val("title") or "", 300),
                url=url,
                summary=clean_text(val("summary") or ""),
                deadline=to_iso(val("deadline")),
                open_date=to_iso(val("open_date")),
                funder=val("funder") or self.funder,
                reference=str(val("reference") or ""),
                funding=str(val("funding") or ""),
                countries=countries if isinstance(countries, list) else [],
                raw_status=str(val("status") or ""),
            )
            if opp.title and self.keep(opp):
                out.append(opp)
        return out
