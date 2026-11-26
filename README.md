# ASEAN Digital Opportunity Tracker

Tracks **grants, calls for proposals, tenders and consulting opportunities** across ASEAN,
ranked for **digital economy** and **workforce planning** work that firms and individual or
group consultants can bid on. It updates automatically every day.

**Dashboard:** https://maygrace06.github.io/ASEAN-Digital/

## What you get

| Output | Where |
|---|---|
| Live dashboard: filters, NEW badges, deadline calendar, pipeline board, source status | [Dashboard](https://maygrace06.github.io/ASEAN-Digital/) |
| Excel workbook and CSV | Download links at the top of the dashboard |
| Daily, weekly, monthly, quarterly and yearly digests | [`reports/`](reports/) (latest: [`reports/LATEST.md`](reports/LATEST.md)) |

Each opportunity shows its title, funder, type, countries, themes, open date, deadline,
status (forthcoming, open, closing soon, closed), funding and eligibility where published,
a relevance score with its breakdown, and the date it was first seen.

## Sources

| Source | What it covers |
|---|---|
| Grants.gov | US federal grants mentioning ASEAN countries |
| EU Funding & Tenders Portal | EU calls and external-action tenders |
| World Bank | Procurement notices in ASEAN countries (awarded contracts excluded) |
| UNDP | Procurement notices, Asia-Pacific |
| DT Global | EOIs, RFPs and RFTs from an implementing partner |
| fundsforNGOs | Latest grants, filtered to ASEAN |
| ASTNET | ASEAN science, technology and innovation calls |
| ASEAN Foundation | Calls for applications |
| The Asia Foundation | Fellowships, grants and RFPs |
| Opportunity Desk | Global opportunities, filtered to ASEAN |
| Google News | Leads to verify on the official site |
| Team list | Opportunities added by hand |

Only items that name an ASEAN country or the region are kept.

**Checked by hand**, because they block automated access or need a login:
[ADB](https://www.adb.org/projects/tenders) ·
[AusConnect (DFAT)](https://ausconnect.dfat.gov.au/opportunities) ·
[AusTender](https://www.tenders.gov.au/) ·
[UNGM](https://www.ungm.org/Public/Notice) ·
[U.S. Mission to ASEAN](https://asean.usmission.gov/) ·
[Asia Foundation procurement](https://asiafoundation.org/procurement/) ·
[GeBIZ](https://www.gebiz.gov.sg) ·
[PhilGEPS](https://notices.philgeps.gov.ph) ·
[Tetra Tech International Development](https://intdev.tetratech.com.au/)

## How the relevance score works

| Signal | Points |
|---|---|
| ASEAN country or region (required) | +25 |
| Digital economy theme | +30 |
| Workforce planning theme | +25 (+5 if both) |
| Focus topic in the title | +15 |
| Consulting work or formal call (RFP, EOI) | +20 |
| Grant, fund or fellowship | +15 |
| Has a deadline | +5 |
| Off-scope work in the title (construction, goods, vehicles…) | −40 |
| News item with no call or grant mentioned | −20 |

Items scoring under 35 are dropped. Hover a score on the dashboard to see how it was worked out.

## Good to know

- Scores are keyword-based. Always confirm eligibility and the exact deadline on the official notice.
- Google News items are leads, not official calls.
- UNDP deadlines are posted in New York time.
