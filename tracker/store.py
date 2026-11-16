"""Persistence: merge new results into data/opportunities.json and track source health."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from .classify import compute_status, setting
from .models import Opportunity
from .utils import ROOT, load_yaml, today

DB = ROOT / "data" / "opportunities.json"
STATE = ROOT / "data" / "state.json"
SCHEDULE_DAYS = {"daily": 0, "weekly": 6, "monthly": 27, "quarterly": 89}


def _read(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def load_db() -> dict[str, Opportunity]:
    return {d["id"]: Opportunity.from_dict(d) for d in _read(DB, [])}


def save_db(db: dict[str, Opportunity]) -> None:
    rows = sorted(db.values(), key=lambda o: (o.deadline or "9999", o.title))
    DB.write_text(json.dumps([o.to_dict() for o in rows], ensure_ascii=False, indent=1), encoding="utf-8")


def load_state() -> dict:
    return _read(STATE, {"sources": {}})


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")


def is_due(src_cfg: dict, state: dict, ref: date | None = None) -> bool:
    ref = ref or today()
    last = (state["sources"].get(src_cfg["id"]) or {}).get("last_ok")
    if not last:
        return True
    gap = SCHEDULE_DAYS.get(src_cfg.get("schedule", "daily"), 0)
    return (ref - date.fromisoformat(last[:10])).days > gap


def merge(db: dict[str, Opportunity], new: list[Opportunity]) -> list[Opportunity]:
    """Upsert; returns the list of brand-new opportunities."""
    stamp = today().isoformat()
    added = []
    for o in new:
        cur = db.get(o.id)
        if cur is None:
            o.first_seen = o.first_seen or stamp
            o.last_seen = stamp
            db[o.id] = o
            added.append(o)
            continue
        for k, v in o.to_dict().items():
            if k in ("first_seen", "id"):
                continue
            if v not in (None, "", [], 0):
                setattr(cur, k, v)
        cur.last_seen = stamp
    return added


def refresh_and_prune(db: dict[str, Opportunity]) -> None:
    keep_days = int(setting("keep_closed_days", 400))
    pipeline = load_pipeline()
    cutoff = today() - timedelta(days=keep_days)
    for oid in list(db):
        o = db[oid]
        o.status = compute_status(o)
        last = o.deadline or o.last_seen or o.first_seen
        if o.status == "closed" and oid not in pipeline and last and date.fromisoformat(last) < cutoff:
            del db[oid]


def load_pipeline() -> dict:
    p = load_yaml("data/pipeline.yaml") or {}
    return {str(k): v for k, v in p.items() if isinstance(v, dict)}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
