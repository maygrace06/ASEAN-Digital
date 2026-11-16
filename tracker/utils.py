"""Shared helpers: config loading, HTTP, dates, text cleanup."""
from __future__ import annotations

import html
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
import yaml
from dateutil import parser as dparser

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("tracker")

USER_AGENT = "ASEAN-Funding-Tracker/1.0 (+https://github.com; research use)"


def load_yaml(rel_path: str | Path) -> Any:
    p = ROOT / rel_path
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


_session: Optional[requests.Session] = None


def http() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})
        _session = s
    return _session


def get(url: str, **kw) -> requests.Response:
    kw.setdefault("timeout", 40)
    r = http().get(url, **kw)
    r.raise_for_status()
    return r


def post(url: str, **kw) -> requests.Response:
    kw.setdefault("timeout", 40)
    r = http().post(url, **kw)
    r.raise_for_status()
    return r


def today() -> date:
    return date.today()


def to_iso(value: Any) -> Optional[str]:
    """Parse almost any date representation into YYYY-MM-DD (or None)."""
    if value in (None, "", []):
        return None
    if isinstance(value, list):
        value = value[0]
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, (int, float)):  # epoch ms or s
        ts = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    s = str(value).strip()
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    try:
        dt = dparser.parse(s, fuzzy=True, dayfirst=not re.match(r"^\d{1,2}/\d{1,2}/\d{4}", s))
        if 2000 <= dt.year <= 2100:
            return dt.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        pass
    return None


_MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE_RX = (
    rf"(\d{{1,2}}[\s\-/]{_MONTHS}[\s\-/,]*\d{{4}}"        # 16 Oct 2026 / 16-Oct-2026
    rf"|{_MONTHS}\s+\d{{1,2}},?\s+\d{{4}}"                # October 16, 2026
    rf"|\d{{4}}-\d{{2}}-\d{{2}}"                          # 2026-10-16
    rf"|\d{{1,2}}/\d{{1,2}}/\d{{4}})"                     # 16/10/2026
)
DEADLINE_RX = re.compile(
    # Strong keywords may have a few words before the date:
    #   "Deadline Date: March 31, 2026", "deadline for submissions is 27 November 2026"
    rf"(?:(?:deadline|closing date|closes?|due date|apply before|submission[s]? (?:due|by)|"
    rf"applications? (?:due|close))[^.!?\d]{{0,50}}?"
    # Weak keywords must be right before the date: "until 5 May 2026", "by 1 June 2026"
    rf"|(?:until|by)\s*[:\-–]?\s*(?:is|on)?\s*){_DATE_RX}",
    re.I,
)
OPEN_RX = re.compile(rf"(?:opens?|opening date|start date|launch(?:ed)?|published|posted)\s*[:\-–]?\s*(?:on)?\s*{_DATE_RX}", re.I)


def find_deadline(text: str) -> Optional[str]:
    m = DEADLINE_RX.search(text or "")
    return to_iso(m.group(1)) if m else None


def find_open_date(text: str) -> Optional[str]:
    m = OPEN_RX.search(text or "")
    return to_iso(m.group(1)) if m else None


def clean_text(html_or_text: str, limit: int = 1200) -> str:
    if not html_or_text:
        return ""
    txt = re.sub(r"<[^>]+>", " ", str(html_or_text))
    txt = html.unescape(txt).replace("\xa0", " ")   # &#38; -> &, &#8230; -> …, &nbsp; -> space
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]


def dig(obj: Any, path: str) -> Any:
    """Read a dotted path like 'data.items.0.title' from nested dict/list."""
    if not path:
        return obj
    cur = obj
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur
