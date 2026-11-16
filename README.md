# ASEAN Digital Economy · Funding Tracker

Tracks **grants, calls for proposals, tenders, funds, fellowships and accelerators** related to the
ASEAN digital economy, AI, future of work, workspace and workforce planning, digital integration and development.
It pulls from public sources on a schedule and writes:

| Output | Where |
|---|---|
| Live dashboard (filters, deadline calendar, pipeline board, source health) | `docs/index.html` → GitHub Pages |
| Excel workbook (Open & upcoming · My pipeline · All) | `exports/opportunities.xlsx` |
| CSV | `exports/opportunities.csv` |
| Daily / weekly / monthly / quarterly / yearly digests | `reports/<period>/*.md` (`reports/LATEST.md` = today) |
| Master database | `data/opportunities.json` |

Each opportunity records: **title, funder, type, countries, themes, open date, deadline, status**
(forthcoming / open / closing soon / closed), **funding amount, eligibility/criteria, requirements**,
reference number, relevance score, first/last seen, and your **pipeline stage**.

---

## How it works

```
config/sources.yaml ──► tracker/sources/*  (fetch: API · RSS · HTML · JSON · manual)
                              │
config/taxonomy.yaml ──► tracker/classify.py (country · theme · type · deadline · relevance score)
                              │
                         tracker/store.py   (merge, de-duplicate, status, prune)  ──► data/opportunities.json
                              │
data/pipeline.yaml ───► tracker/export.py + reports.py ──► exports/, docs/, reports/
```

GitHub Actions runs it every day (06:17 Bangkok). Each source has its own `schedule:`
(`daily` / `weekly` / `monthly`), so slow-moving sites are only checked when due.

### Sources included

| id | Source | Type | Schedule |
|---|---|---|---|
| `grants_gov` | Grants.gov (US federal, keyword search incl. ASEAN countries) | API | daily |
| `eu_portal` | EU Funding & Tenders Portal (calls + EU external-action tenders) | API | daily |
| `worldbank` | World Bank procurement notices, filtered to ASEAN countries | API | daily |
| `fundsforngos_asean` | fundsforNGOs latest feed + fundsforCompanies ASEAN search | RSS | daily |
| `asia_foundation` | The Asia Foundation announcements (fellowships, grants, RFPs) | RSS | weekly |
| `opportunity_desk` | Opportunity Desk (global; only ASEAN items kept) | RSS | daily |
| `dt_global` | DT Global procurements (EOIs, RFPs, RFTs; implementing partner for DFAT etc.) | HTML | daily |
| `undp_procurement` | UNDP procurement notices, Asia-Pacific rows | HTML | daily |
| `astnet` | ASEAN STI Network (ASTIF etc.) | RSS | weekly |
| `google_news_leads` | Google News searches (leads to verify) | RSS | daily |
| `asean_foundation` | ASEAN Foundation call for applications | HTML | weekly |
| `manual` | Your hand-added list `data/manual.yaml` | YAML | daily |
| `example_json` | Template for any JSON API (disabled) | — | — |

Items from non-ASEAN-specific sources are kept only if they mention an ASEAN
country or region (`require_asean_match` in `config/taxonomy.yaml`).

**Check by hand** — these block automated access or need an interactive search,
so they are not fetched: [ADB tenders](https://www.adb.org/projects/tenders),
[U.S. Mission to ASEAN](https://asean.usmission.gov/),
[Asia Foundation procurement](https://asiafoundation.org/procurement/),
[UNGM](https://www.ungm.org/Public/Notice), [GeBIZ](https://www.gebiz.gov.sg),
[PhilGEPS](https://notices.philgeps.gov.ph),
[AusConnect (DFAT)](https://ausconnect.dfat.gov.au/opportunities),
[AusTender](https://www.tenders.gov.au/),
[Tetra Tech International Development](https://intdev.tetratech.com.au/) (EOIs are posted as PDFs, no listing page).

---

## Step-by-step setup

### Step 1 — Install tools on your Mac (one time)

Open **Terminal** and check:

```bash
python3 --version   # need 3.10+
git --version
```

If either is missing: install Python from <https://www.python.org/downloads/> and run
`xcode-select --install` for Git. Create a free account at <https://github.com> if you don't have one.

### Step 2 — Run it locally

```bash
cd ~/Desktop/"Desktop 2"/"ASEAN Funding Tracker"
python3 -m venv .venv
source .venv/bin/activate          # do this each time you open a new Terminal
pip install -r requirements.txt

pytest -q                          # 16 offline tests should pass
python -m tracker run --all        # fetch every enabled source now
python -m tracker sources          # see which sources worked
open exports/opportunities.xlsx    # look at the results
```

To view the dashboard locally:

```bash
cd docs && python3 -m http.server 8000
# open http://localhost:8000 in your browser, Ctrl+C to stop
```

### Step 3 — Create the GitHub repository

1. On GitHub click **New repository** → name it `asean-funding-tracker` → choose **Private** or **Public**
   → do **not** tick "Add a README" → **Create repository**.
2. Back in Terminal (inside the project folder):

```bash
git init
git add .
git commit -m "Initial commit: ASEAN funding tracker"
git branch -M main
git remote add origin https://github.com/<your-username>/asean-funding-tracker.git
git push -u origin main
```

When asked for a password, use a **Personal Access Token** (GitHub → Settings → Developer settings →
Personal access tokens → Fine-grained → give it *Contents: Read and write* on this repo),
or install GitHub Desktop / `gh auth login` to sign in once.

### Step 4 — Let GitHub Actions write data

Repo → **Settings → Actions → General → Workflow permissions** → select
**Read and write permissions** → Save.

Then **Actions** tab → *Fetch funding opportunities* → **Run workflow** → mode `all`.
After ~1–2 minutes a new commit `data: update …` appears with fresh data.

### Step 5 — Turn on the dashboard (GitHub Pages)

Repo → **Settings → Pages** → Source: **Deploy from a branch** → Branch: `main`, folder: **/docs** → Save.
Your dashboard will be at `https://<your-username>.github.io/asean-funding-tracker/`.

> GitHub Pages on a **private** repo needs a paid plan (Pro/Team). On the free plan, either make the
> repo public, or keep it private and use the Excel/CSV files and `reports/` instead.

### Step 6 — Daily routine

- Open the dashboard → **Live** list, **Deadline calendar** (group by week / month / quarter / year).
- Something worth pursuing? Open it → **Copy pipeline entry** → paste into `data/pipeline.yaml`
  (edit directly on GitHub with the ✏️ pencil) and set `stage`, `owner`, `next_action`, `due`.
  Committing triggers a rebuild, and it appears on the **My pipeline** board and in every digest.
- Read `reports/LATEST.md` for today's digest, or `reports/monthly/2026-11.md` etc.
- If a run fails, GitHub emails you automatically. For digests by email/Slack, see "Ideas for next steps".

Pipeline stages: `watching → shortlisted → preparing → submitted → awarded / rejected / withdrawn`.

---

## Customising

### Add an opportunity by hand
Append to `data/manual.yaml` (only `title` and `url` are required).

### Add a new source — no code needed

**RSS feed** (any WordPress site usually has `/feed/`; WordPress search: `/?s=KEYWORD&feed=rss2`):

```yaml
  - id: mdec_news
    name: MDEC news
    type: rss
    enabled: true
    schedule: weekly
    kind: grant
    funder: MDEC
    region_hint: ASEAN           # site is ASEAN-specific, skip region check
    urls: [https://example.my/feed/]
    include: "grant|fund|call|programme"
```

**HTML page** — right-click a listing on the page → *Inspect*, find the repeating element:

```yaml
  - id: depa_calls
    type: html
    url: https://www.example.or.th/en/calls
    item_selector: ".news-item"     # one element per call
    link_selector: "a"
    deadline_selector: ".date"      # optional; otherwise dates are found in the text
    context_parent_levels: 0
```

**Any JSON API** — see the `example_json` block in `config/sources.yaml` (dotted paths map fields).

Test a single source: `python -m tracker run --source depa_calls`, then `python -m tracker sources`.

### Add a new source *type* (Python)
Create `tracker/sources/my_site.py`:

```python
from .base import Source, register
from ..utils import get, to_iso

@register("my_site")
class MySite(Source):
    def fetch(self):
        data = get(self.cfg["url"]).json()
        return [self.make(title=i["name"], url=i["link"], deadline=to_iso(i["close"])) for i in data]
```

…and add `from . import my_site` to `tracker/sources/__init__.py`.

### Change schedules
- Whole job: edit `cron:` in `.github/workflows/fetch.yml` (UTC). `17 23 * * *` = 06:17 Bangkok daily;
  `17 23 * * 1` = Mondays only.
- Per source: `schedule: daily | weekly | monthly` in `sources.yaml`.
- Manual run: Actions → Run workflow (mode `all`, or a single source id).

### Tune relevance
`config/taxonomy.yaml` holds countries, themes and keywords, scoring weights and
`default_min_score` (35). Raise a source's `min_score` if it is noisy; lower it if it misses things.

The score (0–100) is built for: **ASEAN · (1) digital economy · (2) workforce planning ·
consulting work for firms and individual/group consultants, plus grants**.

| Part | Points |
|---|---|
| ASEAN country / region (required) | +25 |
| Digital economy theme (`focus.primary`) | +30 |
| …or workforce planning theme (`focus.secondary`) | +25 (+5 if both) |
| …or only other themes | +10 |
| Focus topic in the **title** | +15 |
| Consulting / advisory work or formal call (`advisory_terms`, RFP, EOI) | +20 |
| …or grant / fund / fellowship | +15 |
| Has a deadline | +5 |
| Off-scope work in the title (`off_scope_terms`: construction, goods, vehicles…) | −40 |
| News lead with no call / grant mentioned | −20 |

Generic words in `weak_terms` (research, youth, innovation…) tag a theme but earn no focus points.
Every item has a `score_why` explanation — hover the score on the dashboard, or open the item.
Stored items are re-scored on every run, so taxonomy edits apply to old items too.

---

## Commands

| Command | What it does |
|---|---|
| `python -m tracker run` | fetch sources that are due |
| `python -m tracker run --all` | fetch every enabled source now |
| `python -m tracker run --source eu_portal` | one source only |
| `python -m tracker report --period monthly` | rebuild a digest (`daily/weekly/monthly/quarterly/yearly`) |
| `python -m tracker export` | rebuild CSV / Excel / dashboard from the database |
| `python -m tracker sources` | list sources + last success / errors |
| `pytest -q` | offline tests |

## Notes & limits
- Source APIs and page layouts change. When one breaks, the run continues and the **Sources** tab
  shows the error. Fix the config (or parser) and re-run.
- `google_news_leads` items are **leads**, not official calls. Always verify on the funder's site.
- Eligibility/requirements are captured where the source provides them (APIs, manual entries);
  for RSS/HTML items the summary text is stored, so open the official page for full criteria.
- Respect each site's terms of use; keep schedules modest (daily or weekly).

## Ideas for next steps
1. Email or Slack digest: add a workflow step that sends `reports/LATEST.md` (e.g. via a Slack webhook secret).
2. More sources: ADB, UNGM, UNDP, national e-procurement (GeBIZ, PhilGEPS, LPSE, e-GP Thailand), MDEC, depa, IMDA, Google.org / Microsoft / AWS programs.
3. AI enrichment: pass new items to an LLM to extract eligibility, budget and criteria into structured fields.
4. Go/no-go scoring: add your own fit criteria (budget size, partner needs, eligibility of your entity type).
