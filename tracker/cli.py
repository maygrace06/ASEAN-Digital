"""Command line entry point.

  python -m tracker run                 # fetch sources that are due (per schedule)
  python -m tracker run --all           # fetch every enabled source now
  python -m tracker run --source eu_portal --source manual
  python -m tracker report --period monthly
  python -m tracker sources             # list sources + health
  python -m tracker export              # rebuild CSV/XLSX/dashboard from the database
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from . import export, reports, store
from .classify import classify, setting
from .sources import REGISTRY
from .utils import load_yaml, log


def _sources() -> list[dict]:
    return (load_yaml("config/sources.yaml") or {}).get("sources", [])


def cmd_run(args) -> int:
    state = store.load_state()
    db = store.load_db()
    default_min = int(setting("default_min_score", 30))
    total_new = 0
    for cfg in _sources():
        sid = cfg["id"]
        if args.source and sid not in args.source:
            continue
        if not cfg.get("enabled", True) and not args.source:
            continue
        if not (args.all or args.source) and not store.is_due(cfg, state):
            log.info("· %-22s not due (%s)", sid, cfg.get("schedule", "daily"))
            continue
        cls = REGISTRY.get(cfg["type"])
        st = state["sources"].setdefault(sid, {})
        st["last_run"] = store.now_iso()
        if not cls:
            st["error"] = f"unknown type '{cfg['type']}'"
            log.error("✗ %s: %s", sid, st["error"])
            continue
        t0 = time.time()
        src = cls(cfg)
        try:
            items = src.fetch()
            if not items and src.errors:
                raise RuntimeError(f"all requests failed — {src.errors[0]}")
        except Exception as e:
            st["error"] = f"{type(e).__name__}: {e}"[:300]
            log.error("✗ %-22s %s", sid, st["error"])
            continue
        min_score = int(cfg.get("min_score", default_min))
        kept = []
        for o in items:
            classify(o, cfg.get("region_hint"))
            if cfg["type"] == "manual" or o.score >= min_score:
                kept.append(o)
        added = store.merge(db, kept)
        total_new += len(added)
        st.update({"last_ok": store.now_iso(), "error": "", "fetched": len(items),
                   "kept": len(kept), "new": len(added), "seconds": round(time.time() - t0, 1),
                   "warnings": src.errors[:5]})
        log.info("✓ %-22s fetched %4d · kept %4d · new %3d", sid, len(items), len(kept), len(added))

    store.refresh_and_prune(db)
    store.save_db(db)
    store.save_state(state)
    export.write_all(db)
    written = reports.write(db)
    log.info("Database: %d opportunities (%d new). Reports: %s", len(db), total_new, ", ".join(written))
    return 0


def cmd_report(args) -> int:
    db = store.load_db()
    store.refresh_and_prune(db)
    paths = reports.write(db, periods=args.period)
    print("\n".join(paths))
    return 0


def cmd_export(args) -> int:
    db = store.load_db()
    store.refresh_and_prune(db)
    store.save_db(db)
    export.write_all(db)
    print("Wrote exports/opportunities.csv, exports/opportunities.xlsx, docs/data.json")
    return 0


def cmd_sources(args) -> int:
    state = store.load_state()["sources"]
    print(f"{'id':24} {'type':11} {'sched':8} {'on':3} {'last ok':26} {'kept':>5}  error")
    for s in _sources():
        st = state.get(s["id"], {})
        print(f"{s['id']:24} {s['type']:11} {s.get('schedule', 'daily'):8} {'y' if s.get('enabled', True) else 'n':3} "
              f"{st.get('last_ok', '-'):26} {st.get('kept', '-'):>5}  {st.get('error', '')}")
    return 0


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(prog="tracker", description="ASEAN digital-economy funding tracker")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="fetch sources")
    r.add_argument("--all", action="store_true", help="ignore schedules, fetch every enabled source")
    r.add_argument("--source", action="append", help="only this source id (repeatable)")
    r.set_defaults(func=cmd_run)
    p = sub.add_parser("report", help="write digests")
    p.add_argument("--period", action="append", choices=["daily", "weekly", "monthly", "quarterly", "yearly"])
    p.set_defaults(func=cmd_report)
    sub.add_parser("export", help="rebuild CSV/XLSX/dashboard").set_defaults(func=cmd_export)
    sub.add_parser("sources", help="list sources + health").set_defaults(func=cmd_sources)
    args = ap.parse_args(argv)
    if args.cmd == "report" and not args.period:
        args.period = ["daily", "weekly", "monthly", "quarterly", "yearly"]
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
