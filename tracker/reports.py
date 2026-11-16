"""Markdown digests: daily, monthly, quarterly, yearly (written to reports/)."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from .models import Opportunity
from .store import load_pipeline
from .utils import ROOT, today

LIVE = ("open", "closing_soon", "forthcoming", "unknown")


def period_bounds(period: str, ref: date) -> tuple[date, date, str]:
    if period == "daily":
        return ref, ref, ref.isoformat()
    if period == "weekly":
        start = ref - timedelta(days=ref.weekday())
        return start, start + timedelta(days=6), f"{ref.isocalendar().year}-W{ref.isocalendar().week:02d}"
    if period == "monthly":
        start = ref.replace(day=1)
        nxt = (start + timedelta(days=32)).replace(day=1)
        return start, nxt - timedelta(days=1), ref.strftime("%Y-%m")
    if period == "quarterly":
        q = (ref.month - 1) // 3
        start = date(ref.year, q * 3 + 1, 1)
        nxt = date(ref.year + (q == 3), (q * 3 + 3) % 12 + 1, 1)
        return start, nxt - timedelta(days=1), f"{ref.year}-Q{q + 1}"
    if period == "yearly":
        return date(ref.year, 1, 1), date(ref.year, 12, 31), str(ref.year)
    raise ValueError(period)


def _line(o: Opportunity, pipe: dict) -> str:
    stage = f" · **{pipe[o.id]['stage']}**" if o.id in pipe and pipe[o.id].get("stage") else ""
    ctry = ", ".join(o.countries[:4]) or "—"
    th = ", ".join(o.themes[:3]) or "—"
    dl = o.deadline or "no deadline"
    return f"- `{o.id}` [{o.title}]({o.url}) — {o.funder or o.source} · {o.kind} · ⏰ {dl} · {ctry} · _{th}_{stage}"


def _between(d: str | None, a: date, b: date) -> bool:
    return bool(d) and a <= date.fromisoformat(d) <= b


def build(db: dict[str, Opportunity], period: str, ref: date | None = None) -> str:
    ref = ref or today()
    start, end, label = period_bounds(period, ref)
    pipe = load_pipeline()
    opps = list(db.values())
    new = [o for o in opps if _between(o.first_seen, start, end)]
    due = sorted([o for o in opps if _between(o.deadline, start, end)], key=lambda o: o.deadline)
    horizon = end + timedelta(days=30 if period != "yearly" else 90)
    upcoming = sorted([o for o in opps if o.status in LIVE and _between(o.deadline, ref, horizon)],
                      key=lambda o: o.deadline)
    live = [o for o in opps if o.status in LIVE]

    md = [f"# {period.capitalize()} funding digest — {label}",
          f"_Period {start} → {end} · generated {ref}_\n",
          f"**{len(live)}** live opportunities · **{len(new)}** new this period · "
          f"**{len(due)}** deadlines this period · **{len(pipe)}** in your pipeline\n"]

    if pipe:
        md.append("## 🎯 Pipeline")
        for oid, p in sorted(pipe.items(), key=lambda kv: str(kv[1].get("due") or "9999")):
            o = db.get(oid)
            name = f"[{o.title}]({o.url})" if o else f"`{oid}` (not in database)"
            md.append(f"- **{p.get('stage', '?')}** · {name} · next: {p.get('next_action', '—')} "
                      f"· due {p.get('due', '—')} · deadline {o.deadline if o else '—'}")
        md.append("")

    md.append(f"## ⏰ Deadlines ahead (to {horizon})")
    md += [_line(o, pipe) for o in upcoming] or ["_None_"]
    md.append("")

    md.append("## 🆕 New this period")
    md += [_line(o, pipe) for o in sorted(new, key=lambda o: -o.score)[:150]] or ["_None_"]
    md.append("")

    if period in ("monthly", "quarterly", "yearly"):
        scope = new or live
        md.append("## 📊 Breakdown (new this period)")
        for title, counter in (("By theme", Counter(t for o in scope for t in o.themes)),
                               ("By country", Counter(c for o in scope for c in o.countries)),
                               ("By type", Counter(o.kind for o in scope)),
                               ("By source", Counter(o.source for o in scope))):
            md.append(f"**{title}:** " + (", ".join(f"{k} ({v})" for k, v in counter.most_common()) or "—"))
        md.append("")
        md.append("## ✅ Deadlines that fell in this period")
        md += [_line(o, pipe) for o in due] or ["_None_"]

    return "\n".join(md) + "\n"


def write(db: dict[str, Opportunity], periods=("daily", "monthly", "quarterly", "yearly"), ref=None) -> list[str]:
    ref = ref or today()
    written = []
    for p in periods:
        _, _, label = period_bounds(p, ref)
        folder = ROOT / "reports" / p
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{label}.md"
        path.write_text(build(db, p, ref), encoding="utf-8")
        written.append(str(path.relative_to(ROOT)))
    # convenience pointer to the newest daily digest
    (ROOT / "reports" / "LATEST.md").write_text(build(db, "daily", ref), encoding="utf-8")
    return written
