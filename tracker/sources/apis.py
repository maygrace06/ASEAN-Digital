"""Built-in connectors for public funding/procurement APIs.

Each API is queried once per keyword in the source's `keywords` list,
results are de-duplicated by the store afterwards.
"""
from __future__ import annotations

import json

from ..utils import clean_text, get, post, to_iso
from .base import Source, register


# ---------------------------------------------------------------- Grants.gov
@register("grants_gov")
class GrantsGov(Source):
    """https://grants.gov/api/api-guide — search2 needs no API key."""
    URL = "https://api.grants.gov/v1/api/search2"

    def fetch(self):
        out = []
        for kw in self.cfg.get("keywords", ["ASEAN"]):
            body = {"keyword": kw, "oppStatuses": self.cfg.get("statuses", "forecasted|posted"),
                    "rows": int(self.cfg.get("rows", 100))}
            try:
                data = post(self.URL, json=body).json()
            except Exception as e:
                self.warn(kw, e)
                continue
            for h in (data.get("data") or {}).get("oppHits", []):
                out.append(self.make(
                    title=clean_text(h.get("title", ""), 300),
                    url=f"https://www.grants.gov/search-results-detail/{h.get('id')}",
                    funder=h.get("agency") or h.get("agencyName") or h.get("agencyCode") or "US Government",
                    reference=h.get("number", ""),
                    open_date=to_iso(h.get("openDate")),
                    deadline=to_iso(h.get("closeDate")),
                    raw_status=h.get("oppStatus", ""),
                    summary=f"Search keyword: {kw}. Doc type: {h.get('docType', '')}. "
                            f"ALN: {', '.join(h.get('alnist') or h.get('cfdaList') or [])}",
                ))
        return [o for o in out if self.keep(o)]


# ------------------------------------------------------- EU Funding & Tenders
@register("eu_portal")
class EuPortal(Source):
    """EU Funding & Tenders Portal public search API (SEDIA)."""
    URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    TOPIC = "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{}"
    STATUS = {"31094501": "forthcoming", "31094502": "open", "31094503": "closed"}

    def fetch(self):
        query = {"bool": {"must": [
            # 0 = tenders / EU external-action notices, 1 = calls, 2 = EuropeAid, 8 = cascade calls
            {"terms": {"type": self.cfg.get("types", ["0", "1", "2", "8"])}},
            {"terms": {"status": ["31094501", "31094502"]}},
        ]}}
        out = []
        for kw in self.cfg.get("keywords", ["ASEAN"]):
            params = {"apiKey": "SEDIA", "text": kw, "pageSize": 100, "pageNumber": 1}
            files = {
                "query": ("blob", json.dumps(query), "application/json"),
                "languages": ("blob", json.dumps(["en"]), "application/json"),
            }
            try:
                data = post(self.URL, params=params, files=files).json()
            except Exception as e:
                self.warn(kw, e)
                continue
            for r in data.get("results", []):
                md = r.get("metadata", {}) or {}
                first = lambda k: (md.get(k) or [None])[0]  # noqa: E731
                ident = first("identifier") or first("callIdentifier") or ""
                title = first("title") or r.get("summary") or r.get("content") or ""
                status_code = str(first("status") or "")
                is_tender = str(first("type") or "") == "0"
                out.append(self.make(
                    title=clean_text(f"{title}", 300),
                    kind="tender" if is_tender else self.kind,
                    url=r.get("url") or (self.TOPIC.format(ident.lower()) if ident else ""),
                    reference=ident,
                    summary=clean_text(first("descriptionByte") or first("callTitle") or r.get("summary") or ""),
                    open_date=to_iso(first("startDate")),
                    deadline=to_iso(first("deadlineDate")),
                    raw_status=self.STATUS.get(status_code, status_code),
                    funding=str(first("budget") or ""),
                ))
        return [o for o in out if o.title and self.keep(o)]


# ----------------------------------------------------------------- World Bank
ASEAN_WB_NAMES = {
    "indonesia": "Indonesia", "philippines": "Philippines", "viet nam": "Vietnam", "vietnam": "Vietnam",
    "cambodia": "Cambodia", "lao people's democratic republic": "Laos", "lao pdr": "Laos",
    "myanmar": "Myanmar", "thailand": "Thailand", "malaysia": "Malaysia", "timor-leste": "Timor-Leste",
    "singapore": "Singapore", "brunei darussalam": "Brunei",
    "east asia and pacific": "ASEAN-wide",
}


@register("worldbank")
class WorldBank(Source):
    URL = "https://search.worldbank.org/api/v2/procnotices"
    DETAIL = "https://projects.worldbank.org/en/projects-operations/procurement-detail/{}"

    def fetch(self):
        out = []
        for kw in self.cfg.get("keywords", ["digital"]):
            params = {"format": "json", "rows": int(self.cfg.get("rows", 200)), "qterm": kw,
                      "srt": "noticedate", "order": "desc"}
            try:
                data = get(self.URL, params=params).json()
            except Exception as e:
                self.warn(kw, e)
                continue
            for n in data.get("procnotices", []) or []:
                ctry = (n.get("project_ctry_name") or "").strip()
                country = ASEAN_WB_NAMES.get(ctry.lower())
                if not country:
                    continue  # keep only ASEAN countries
                out.append(self.make(
                    title=clean_text(n.get("bid_description") or n.get("project_name") or "", 300),
                    url=self.DETAIL.format(n.get("id")),
                    reference=n.get("bid_reference_no") or n.get("id", ""),
                    funder=f"World Bank – {n.get('project_name', '')}".strip(" –"),
                    countries=[country],
                    summary=clean_text(f"{n.get('notice_type', '')}. {n.get('procurement_group', '')}. "
                                       f"Project: {n.get('project_name', '')} ({n.get('project_id', '')}). "
                                       f"{n.get('notice_text', '')}"),
                    open_date=to_iso(n.get("noticedate")),
                    deadline=to_iso(n.get("submission_deadline_date")),
                    raw_status=n.get("notice_status", ""),
                ))
        return [o for o in out if self.keep(o)]
