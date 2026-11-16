"""Offline tests: every parser is fed a sample payload (no internet needed).

Run:  pytest -q
"""
from datetime import date, timedelta

import pytest

from tracker import classify as C
from tracker.models import Opportunity
from tracker.sources import REGISTRY
from tracker.sources import apis, html, rss

FUTURE = (date.today() + timedelta(days=60)).isoformat()
SOON = (date.today() + timedelta(days=5)).isoformat()


class FakeResp:
    def __init__(self, data=None, text="", content=b""):
        self._data, self.text, self.content = data, text, content or text.encode()

    def json(self):
        return self._data


def test_deadline_extraction():
    assert C.find_deadline("Deadline: 16-Oct-2026") == "2026-10-16"
    assert C.find_deadline("Applications close on January 7, 2027.") == "2027-01-07"
    assert C.find_deadline("Apply Before: 30 October 2026") == "2026-10-30"


def test_classify_scores_asean_ai():
    o = Opportunity(title="Call for Proposals: AI for MSME digital skills in Vietnam and Indonesia",
                    url="https://x.org/a", source="t", summary=f"Deadline: {FUTURE}")
    C.classify(o)
    assert set(o.countries) >= {"Vietnam", "Indonesia"}
    assert "AI & Data" in o.themes and "Future of Work & Skills" in o.themes
    assert o.score >= 80 and o.status == "open"


def test_irrelevant_item_scores_low():
    o = Opportunity(title="Coastal communities fund (United Kingdom)", url="https://x.org/b", source="t")
    C.classify(o)
    assert o.score < 30


def test_thai_does_not_match_ai():
    o = Opportunity(title="Thai rice farmers training", url="https://x.org/c", source="t")
    C.classify(o)
    assert "AI & Data" not in o.themes and o.countries == ["Thailand"]


def test_status_closing_soon_and_forthcoming():
    assert C.compute_status(Opportunity(title="a", url="u", source="s", deadline=SOON)) == "closing_soon"
    assert C.compute_status(Opportunity(title="a", url="u", source="s", open_date=FUTURE)) == "forthcoming"


def test_grants_gov(monkeypatch):
    payload = {"data": {"oppHits": [{"id": "123", "number": "OFOP0002648", "title": "Y-AI Indo-Pacific",
                                     "agency": "Department of State", "openDate": "06/04/2026",
                                     "closeDate": "07/05/2026", "oppStatus": "posted"}]}}
    monkeypatch.setattr(apis, "post", lambda *a, **k: FakeResp(payload))
    out = apis.GrantsGov({"id": "g", "keywords": ["ASEAN"]}).fetch()
    assert out[0].deadline == "2026-07-05" and out[0].reference == "OFOP0002648"
    assert out[0].url.endswith("/123")


def test_eu_portal(monkeypatch):
    payload = {"results": [{"metadata": {"identifier": ["DIGITAL-2026-AI-01"], "title": ["AI Continent"],
                                         "deadlineDate": ["2027-02-10T17:00:00.000+0100"],
                                         "startDate": ["2026-11-01T00:00:00.000+0100"],
                                         "status": ["31094502"]}}]}
    monkeypatch.setattr(apis, "post", lambda *a, **k: FakeResp(payload))
    o = apis.EuPortal({"id": "eu", "keywords": ["ASEAN"]}).fetch()[0]
    assert o.deadline == "2027-02-10" and o.raw_status == "open" and "digital-2026-ai-01" in o.url


def test_worldbank_filters_asean(monkeypatch):
    payload = {"procnotices": [
        {"id": "OP1", "project_ctry_name": "Viet Nam", "bid_description": "Digital skills platform",
         "submission_deadline_date": "2027-01-15T00:00:00Z", "noticedate": "01-Nov-2026"},
        {"id": "OP2", "project_ctry_name": "Kenya", "bid_description": "ICT"}]}
    monkeypatch.setattr(apis, "get", lambda *a, **k: FakeResp(payload))
    out = apis.WorldBank({"id": "wb", "keywords": ["digital"]}).fetch()
    assert len(out) == 1 and out[0].countries == ["Vietnam"] and out[0].deadline == "2027-01-15"


def test_rss(monkeypatch):
    xml = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
    <item><title>Call for Applications: ASEAN Digital Innovation Grant</title>
    <link>https://example.org/x</link><description>Deadline: 16-Dec-2026. AI startups.</description>
    <pubDate>Mon, 02 Nov 2026 10:00:00 +0000</pubDate></item></channel></rss>"""
    monkeypatch.setattr(rss, "get", lambda *a, **k: FakeResp(text=xml))
    out = rss.RssSource({"id": "r", "urls": ["https://e"], "include": "call|grant"}).fetch()
    assert out[0].title.startswith("Call for Applications") and out[0].open_date == "2026-11-02"


def test_html(monkeypatch):
    page = """<div class="list"><div class="card"><h4><a href="/call/a">ASEAN Youth Digital Call</a></h4>
      <p>Published: 1 Nov 2026</p><p>Apply Before: 30 December 2026</p></div>
      <div class="card"><h4><a href="/call/b">Old call</a></h4><p>Registration Closed</p></div></div>"""
    monkeypatch.setattr(html, "get", lambda *a, **k: FakeResp(text=page))
    cfg = {"id": "h", "url": "https://site.org/calls/", "item_selector": "h4", "link_selector": "a",
           "context_parent_levels": 1, "skip_if_text": "Registration Closed"}
    out = html.HtmlSource(cfg).fetch()
    assert len(out) == 1 and out[0].url == "https://site.org/call/a" and out[0].deadline == "2026-12-30"


def test_all_types_registered():
    for t in ("rss", "html", "json_api", "manual", "grants_gov", "eu_portal", "worldbank"):
        assert t in REGISTRY


@pytest.mark.parametrize("period", ["daily", "weekly", "monthly", "quarterly", "yearly"])
def test_report_builds(period):
    from tracker import reports
    o = Opportunity(title="X", url="https://x", source="s", deadline=FUTURE, first_seen=date.today().isoformat())
    C.classify(o)
    md = reports.build({o.id: o}, period)
    assert md.startswith(f"# {period.capitalize()} funding digest")
