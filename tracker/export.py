"""Write CSV, Excel and the dashboard JSON."""
from __future__ import annotations

import csv
import json
import shutil

from .models import Opportunity
from .store import load_pipeline, load_state, now_iso
from .utils import ROOT, load_yaml

COLUMNS = ["id", "status", "deadline", "open_date", "title", "kind", "funder", "countries", "themes",
           "funding", "eligibility", "requirements", "score", "source", "url", "reference",
           "recurring", "notes", "first_seen", "last_seen",
           "pipeline_stage", "pipeline_priority", "pipeline_owner", "pipeline_next_action", "pipeline_due"]


def _rows(db: dict[str, Opportunity]) -> list[dict]:
    pipe = load_pipeline()
    rows = []
    for o in sorted(db.values(), key=lambda o: (o.status == "closed", o.deadline or "9999", -o.score)):
        d = o.to_dict()
        p = pipe.get(o.id, {})
        for k in ("stage", "priority", "owner", "next_action", "due"):
            d[f"pipeline_{k}"] = str(p.get(k, "") or "")
        rows.append(d)
    return rows


def write_all(db: dict[str, Opportunity]) -> None:
    rows = _rows(db)
    (ROOT / "exports").mkdir(exist_ok=True)
    (ROOT / "docs").mkdir(exist_ok=True)

    # CSV
    with open(ROOT / "exports" / "opportunities.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: "; ".join(v) if isinstance(v, list) else v for k, v in r.items()})

    # Excel (optional dependency)
    try:
        _write_xlsx(rows)
    except ImportError:
        pass

    # Dashboard JSON
    sources = {s["id"]: {"name": s.get("name", s["id"]), "type": s["type"], "enabled": s.get("enabled", True),
                         "schedule": s.get("schedule", "daily")}
               for s in (load_yaml("config/sources.yaml") or {}).get("sources", [])}
    for sid, st in load_state().get("sources", {}).items():
        sources.setdefault(sid, {"name": sid}).update(st)
    # copies for GitHub Pages (only /docs is published)
    dl = ROOT / "docs" / "downloads"
    dl.mkdir(exist_ok=True)
    for name in ("opportunities.csv", "opportunities.xlsx"):
        src = ROOT / "exports" / name
        if src.exists():
            shutil.copyfile(src, dl / name)
    payload = {"generated_at": now_iso(), "opportunities": rows, "sources": sources}
    (ROOT / "docs" / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_xlsx(rows):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    sheets = {
        "Open & upcoming": [r for r in rows if r["status"] in ("open", "closing_soon", "forthcoming", "unknown")],
        "My pipeline": [r for r in rows if r.get("pipeline_stage")],
        "All": rows,
    }
    first = True
    for name, data in sheets.items():
        ws = wb.active if first else wb.create_sheet()
        first = False
        ws.title = name
        ws.append(COLUMNS)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F4E79")
        for r in data:
            ws.append(["; ".join(r[k]) if isinstance(r.get(k), list) else r.get(k, "") for k in COLUMNS])
        widths = {"title": 60, "eligibility": 50, "requirements": 50, "url": 40, "funder": 28, "themes": 30}
        for i, col in enumerate(COLUMNS, 1):
            ws.column_dimensions[get_column_letter(i)].width = widths.get(col, 14)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    wb.save(ROOT / "exports" / "opportunities.xlsx")
