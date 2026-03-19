# ARIS — AI Regulation Intelligence System

**Monitor. Baseline. Interpret. Consolidate. Trend. Horizon. Learn. Act.**

ARIS is a fully local, agentic system that monitors AI-related legislation and regulations across US Federal agencies, US state legislatures, and international jurisdictions. It ships with 19 curated baseline regulations, fetches live documents from official government APIs, uses Claude to interpret and analyse them, detects changes, tracks regulatory velocity, scans the regulatory horizon for planned regulations, consolidates obligations across all sources, and performs company-specific compliance gap analysis — all through a browser dashboard or the command line.

Everything runs on your machine. The 19 regulatory baselines, consolidation register, velocity analytics, and horizon calendar require no Claude API calls.

---

## What It Does

| # | Feature | API Calls | Description |
|---|---------|-----------|-------------|
| 1 | **Baselines** | None | 19 curated baseline regulations covering settled AI law. Always available. |
| 2 | **Fetch** | None | Pulls documents from Federal Register, Regulations.gov, Congress.gov, EUR-Lex, UK Parliament, Canada, and state legislatures. |
| 3 | **Filter** | None | Keyword pre-screening and source-quality scoring before any Claude call. |
| 4 | **Interpret** | Claude | Plain-English summaries, urgency ratings, requirements, action items, deadlines. |
| 5 | **Change detection** | Claude | Baseline-aware diffs — compares new documents against the settled baseline, not just against each other. |
| 6 | **Consolidation** | Optional | De-duplicated obligation register from all 19 baselines. Fast mode: zero API calls. Full mode: one Claude call. |
| 7 | **Trends & velocity** | None | Jurisdiction velocity charts, impact-area heatmap, acceleration alerts — from your database, no additional API calls. |
| 8 | **Horizon scanning** | None | Monitors Unified Regulatory Agenda, congressional hearings, EU Work Programme, and UK Parliament upcoming business for regulations planned but not yet published. |
| 9 | **Synthesis** | Claude | Cross-document regulatory landscape with conflict detection. |
| 10 | **Gap analysis** | Claude | Company-profile compliance gaps anchored to specific document IDs. |
| 11 | **Document review** | None | Feedback marks documents Relevant / Partially Relevant / Not Relevant. Not-relevant documents move to an archive. Reviewed documents show a badge so you don't re-review them. |
| 12 | **Learning** | Claude (periodic) | Adapts keyword weights, source-quality scores, and prompt instructions from your feedback. |
| 13 | **PDFs** | None | Auto-download PDFs from Federal Register, EUR-Lex, UK legislation; accept manually supplied PDFs. |

---

## Browser Views

| View | What It Shows |
|------|---------------|
| **Dashboard** | Setup progress, baseline coverage, horizon preview, live urgency stats (once documents exist) |
| **Documents** | Active document list with review badges; Archive tab for not-relevant documents |
| **Changes** | Version diffs with severity badges and side-by-side requirement comparisons |
| **Baselines** | Browse all 19 baseline regulations — obligations, prohibitions, timelines, penalties |
| **Trends** | Jurisdiction velocity line charts, impact-area heatmap, acceleration alerts |
| **Horizon** | 12-month forward calendar of planned/advancing regulations, grouped by month |
| **Synthesis** | Cross-jurisdiction regulatory narratives and conflict maps |
| **Gap Analysis** | Company profiles, gap cards by severity, Obligation Register tab, phased roadmap |
| **PDF Ingest** | Upload PDFs or trigger auto-download |
| **Run Agents** | Trigger fetch/summarise with live log output |
| **Watchlist** | Keyword-based alerts across all documents |
| **Graph** | Document relationship network |
| **Learning** | Source quality profiles, keyword weights, prompt adaptations, feedback history |
| **Settings** | API key status, jurisdiction toggles, database stats |

---

## Baseline Coverage (19 baselines — no API calls required)

### European Union
| Baseline | Status | Covers |
|----------|--------|--------|
| EU AI Act (Regulation 2024/1689) | In Force | Risk tiers, prohibitions, high-risk AI obligations, GPAI, penalties up to €35M / 7% |
| EU GDPR — AI Provisions | In Force | Article 22 automated decisions, DPIAs, purpose limitation |
| EU DSA/DMA — AI Provisions | In Force | Recommender transparency, VLOP systemic risk, gatekeeper rules |
| EU AI Liability + Product Liability Directives | Mixed | Strict liability for defective AI, rebuttable presumption, evidence disclosure |

### US Federal
| Baseline | Status | Covers |
|----------|--------|--------|
| Executive Order 14110 | In Force | Foundation model reporting, NIST direction, agency requirements |
| NIST AI RMF 1.0 | Published | GOVERN / MAP / MEASURE / MANAGE functions |
| FTC AI Guidance | Active | Deceptive AI claims, algorithmic discrimination, FCRA |
| US Sector AI Rules | Active | CFPB, EEOC, FDA, OCC, HHS sector-specific obligations |

### US States
| Baseline | Jurisdiction | Status | Covers |
|----------|-------------|--------|--------|
| NYC Local Law 144 | New York City | In Force | Annual bias audits, AEDTs, 10-day candidate notice |
| California AI Laws | California | Multiple | Training data transparency, AI content disclosure |
| Illinois AI Policy Act | Illinois | In Force | Employer AI notice, bias audits, anti-discrimination |
| Colorado AI Act | Colorado | In Force (Feb 2026) | High-risk AI assessments, human review, deployer governance |

### United Kingdom
| Baseline | Status | Covers |
|----------|--------|--------|
| UK AI Framework + ICO AI Guidance | Active | Five cross-sector principles, sector regulators, UK GDPR Article 22 |

### Canada
| Baseline | Status | Covers |
|----------|--------|--------|
| Canada AIDA (Bill C-27) | Proposed | High-impact AI obligations, risk assessment, incident notification |

### Asia-Pacific
| Baseline | Jurisdiction | Status | Covers |
|----------|-------------|--------|--------|
| Singapore AI Governance Framework | Singapore | Active | 11 governance areas, AI Verify, PDPA obligations |
| Australia AI Governance Framework | Australia | Active | 8 ethics principles, 10 safety guardrails |
| Japan AI Guidelines | Japan | Active | METI 7 principles, APPI obligations, AISI rules |

### Latin America
| Baseline | Jurisdiction | Status | Covers |
|----------|-------------|--------|--------|
| Brazil AI (LGPD + PL 2338/2023) | Brazil | Mixed | LGPD Article 20, AI Bill risk classification, worker rights |

### International
| Baseline | Status | Covers |
|----------|--------|--------|
| OECD AI Principles + G7 Hiroshima Code | Active | 5 OECD pillars, G7 11-point code for advanced AI |

---

## Live API Sources

**US Federal** — Federal Register, Regulations.gov, Congress.gov (free API keys)

**US States** — LegiScan API (50-state coverage); Pennsylvania also uses PA General Assembly XML feed

**International** — EU (EUR-Lex SPARQL + EU AI Office RSS), UK (Parliament Bills API + legislation.gov.uk), Canada (OpenParliament + Canada Gazette RSS)

**Horizon** — Unified Regulatory Agenda (reginfo.gov, no key), Congress.gov hearing schedules (existing key), EU Commission Work Programme (EUR-Lex SPARQL, no key), UK Parliament whatson API (no key)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pdfplumber pypdf   # optional, for PDF extraction

# 2. Configure API keys
copy config\keys.env.example config\keys.env   # Windows
# cp config/keys.env.example config/keys.env   # Mac/Linux
# edit config/keys.env and fill in your keys

# 3. Build the UI (requires Node.js)
cd ui && npm install && npm run build && cd ..

# 4. Run database migration (creates all tables)
python migrate.py

# 5. Verify installation
python main.py status

# 6. Start the server
python server.py
# Open http://localhost:8000
```

---

## Common Commands

```bash
# ── Fetch & analyse ───────────────────────────────────────────────────────────
python main.py run                           # fetch all sources + summarise
python main.py fetch                         # fetch only (no Claude)
python main.py fetch --source federal        # specific source: federal | states | international | horizon
python main.py fetch --days 90              # longer lookback
python main.py summarize                     # summarise pending documents
python main.py summarize --limit 10         # limit to 10 documents

# ── Baselines (no API calls) ──────────────────────────────────────────────────
python main.py baselines                     # list all 19 baselines
python main.py baselines --jurisdiction EU  # filter by jurisdiction

# ── Changes ───────────────────────────────────────────────────────────────────
python main.py changes [--severity X] [--unreviewed]
python main.py diff DOC_A DOC_B

# ── Synthesis ─────────────────────────────────────────────────────────────────
python main.py synthesise "topic" [-j JURS]
python main.py synthesis-topics

# ── Gap analysis ──────────────────────────────────────────────────────────────
python main.py gap-profiles
python main.py gap-analyse PROFILE_ID

# ── PDF ───────────────────────────────────────────────────────────────────────
python main.py pdf-download [--limit N]
python main.py pdf-inbox

# ── Monitoring ────────────────────────────────────────────────────────────────
python main.py watch [--interval 24]         # run every N hours continuously

# ── System ────────────────────────────────────────────────────────────────────
python main.py status
python migrate.py                            # safe to re-run; adds missing tables/columns
```

---

## Folder Structure

```
ai-reg-tracker/
├── main.py                          ← CLI entry point
├── server.py                        ← FastAPI REST server (port 8000)
├── migrate.py                       ← Database migration (run after updates)
├── requirements.txt
│
├── config/
│   ├── keys.env                     ← Your API keys (never commit this)
│   ├── keys.env.example             ← Template
│   ├── settings.py                  ← Global settings, AI keywords, paths
│   └── jurisdictions.py             ← Toggle which jurisdictions are monitored
│
├── data/
│   └── baselines/                   ← 19 static JSON baseline files (no API)
│       ├── index.json
│       ├── eu_ai_act.json
│       ├── eu_gdpr_ai.json
│       ├── eu_dsa_dma.json
│       ├── eu_ai_liability.json
│       ├── us_eo_14110.json
│       ├── us_nist_ai_rmf.json
│       ├── us_ftc_ai.json
│       ├── us_sector_ai.json
│       ├── uk_ai_framework.json
│       ├── canada_aida.json
│       ├── illinois_aipa.json
│       ├── colorado_ai.json
│       ├── nyc_ll144.json
│       ├── california_ai.json
│       ├── singapore_ai.json
│       ├── australia_ai.json
│       ├── japan_ai.json
│       ├── brazil_ai.json
│       └── oecd_ai_principles.json
│
├── agents/
│   ├── baseline_agent.py            ← Loads and queries baselines (no API)
│   ├── consolidation_agent.py       ← De-duplicated obligation register (optional Claude)
│   ├── diff_agent.py                ← Baseline-aware version comparison
│   ├── gap_analysis_agent.py        ← Company-profile compliance gap analysis
│   ├── interpreter.py               ← Claude document analysis + pre-filter
│   ├── learning_agent.py            ← Adaptive keyword/source scoring from feedback
│   ├── orchestrator.py              ← Coordinates all four fetch tracks
│   ├── scheduler.py                 ← Watch mode / recurring runs
│   ├── synthesis_agent.py           ← Cross-document synthesis + conflict detection
│   └── trend_agent.py               ← Velocity analytics, heatmap, alerts (no API)
│
├── sources/
│   ├── federal_agent.py             ← Federal Register, Regulations.gov, Congress.gov
│   ├── horizon_agent.py             ← Regulatory horizon scanning (no API key needed)
│   ├── pdf_agent.py                 ← PDF extraction, auto-download, drop folder
│   ├── state_agent_base.py
│   ├── states/
│   │   └── pennsylvania.py
│   └── international/
│       ├── eu.py
│       ├── uk.py
│       ├── canada.py
│       └── stubs.py
│
├── utils/
│   ├── db.py                        ← SQLite tables + CRUD (17 tables)
│   ├── cache.py                     ← HTTP cache, keyword scoring helpers
│   └── reporter.py
│
├── tests/
│   ├── test_suite.py                ← Federal + PA agent tests
│   ├── test_international.py        ← EU, UK, Canada
│   ├── test_diff.py                 ← Diff agent + change detection
│   ├── test_learning.py             ← Learning agent + feedback
│   ├── test_synthesis.py            ← Synthesis agent
│   ├── test_pdf.py                  ← PDF extraction
│   ├── test_gap_analysis.py         ← Gap analysis agent
│   ├── test_baselines.py            ← All 19 baseline files
│   ├── test_consolidation.py        ← Consolidation agent
│   ├── test_trends.py               ← Trend/velocity agent
│   └── test_horizon.py              ← Horizon scanning agent
│
└── ui/src/views/
    ├── Dashboard.jsx                ← Setup guide, baseline coverage, horizon preview
    ├── Documents.jsx                ← Active + Archive tabs, review badges
    ├── Changes.jsx                  ← Version diffs with severity
    ├── Baselines.jsx                ← Browse all 19 baselines
    ├── Trends.jsx                   ← Velocity charts, heatmap, alerts
    ├── Horizon.jsx                  ← Forward calendar, timeline/list views
    ├── Synthesis.jsx                ← Cross-document narratives
    ├── GapAnalysis.jsx              ← Profiles, gaps, Register tab, roadmap
    ├── PDFIngest.jsx
    ├── RunAgents.jsx
    ├── Watchlist.jsx
    ├── Graph.jsx
    ├── Learning.jsx                 ← Feedback buttons exported from here
    └── Settings.jsx
```

---

## Database Tables (17 tables)

| Table | Purpose |
|-------|---------|
| `documents` | Raw documents fetched from sources |
| `summaries` | Claude-generated summaries with urgency, requirements, impact areas |
| `document_diffs` | Version comparisons with severity and requirement changes |
| `document_links` | Relationships between documents (supersedes, amends, etc.) |
| `pdf_metadata` | PDF extraction records |
| `feedback_events` | Human relevance feedback (relevant / not_relevant / partially_relevant) |
| `source_profiles` | Rolling quality scores per source and agency |
| `keyword_weights` | Learned keyword multipliers from feedback |
| `prompt_adaptations` | Claude-generated prompt notes for problematic sources |
| `fetch_history` | Fetch run log |
| `thematic_syntheses` | Cross-document synthesis results |
| `company_profiles` | Company profiles for gap analysis |
| `gap_analyses` | Gap analysis results (history preserved) |
| `regulatory_horizon` | Forward-looking horizon items from regulatory calendars |
| `trend_snapshots` | Cached velocity / heatmap / alert data (refreshed daily) |
| `obligation_register_cache` | Cached consolidation register results |

---

## Key Concepts

### Four Fetch Tracks

**Track 1 — US Federal:** Federal Register rules, proposed rules, and notices. Regulations.gov dockets. Congress.gov bills.

**Track 2 — US States:** LegiScan 50-state API. Pennsylvania additionally uses the PA General Assembly XML feed.

**Track 3 — International:** EUR-Lex SPARQL for EU legislation. UK Parliament Bills API. OpenParliament and Canada Gazette for Canada.

**Track 4 — Horizon:** Unified Regulatory Agenda (planned US federal rulemakings with anticipated dates), congressional committee hearing schedules, EU Commission Work Programme, UK Parliament upcoming bill stages. No additional API keys required. Documents that have not yet been published but are planned or advancing.

### How Baseline Integration Works

Before any Claude analysis, the relevant baseline for a document's jurisdiction is loaded and prepended to the prompt. This means:

- **Diff agent** — compares a new document against what the Act *requires*, not just against a prior version. Flags when a change adds, removes, or contradicts a baseline obligation.
- **Gap analysis** — scope mapping includes the full settled body of law regardless of how many documents are in the database. A company profile against the EU AI Act gets all 40+ baseline obligations even if only 5 EU documents have been fetched.
- **Consolidation** — the register is built from baseline obligations as its foundation, with live documents augmenting it.

### Consolidation Register

The `ConsolidationAgent` produces a single de-duplicated list of what you must actually do across all your jurisdictions. Two modes:

- **Fast** (no API) — structural consolidation using fuzzy title matching and keyword-based category assignment. Runs in under 100ms. Always available.
- **Full** (one Claude call, cached 24h) — semantic deduplication catches near-identical obligations phrased differently across jurisdictions.

Each register entry has: a clear action-verb title, category, description, strictest scope version, sources list (all regulations that impose it), earliest deadline, and universality (Universal / Majority / Single jurisdiction).

### Regulatory Velocity

The `TrendAgent` computes, from your local database with no API calls:

- **Velocity** — documents per jurisdiction per 30-day window over 12 months, with trend labels (accelerating / stable / decelerating)
- **Heatmap** — impact areas ranked by activity score combining recent volume and urgency weighting
- **Alerts** — jurisdictions and impact areas whose document count has increased ≥50% vs 6 months prior

Results are cached in `trend_snapshots` and refreshed automatically after every `python main.py run`.

### Document Review Workflow

Documents flow through three states:

1. **Unreviewed** — no badge shown in the list
2. **Reviewed** — green check (Relevant) or yellow minus (Partially Relevant) badge shown on the list row; the feedback section shows "Marked Relevant" when you re-open the document
3. **Archived** — marked Not Relevant; removed from the active list immediately; accessible under the Archive tab; feedback buttons hidden in the detail panel

### Learning System

Every Not Relevant mark does three things: decreases the source's quality score, decreases the agency's score separately, and reduces the weights of matched keywords. After 5+ false positives from one source within 30 days, Claude generates a targeted instruction prepended to all future prompts for that source. These adaptations are viewable and toggleable in the Learning view.

---

## Running Tests

```bash
python -m pytest tests/ -v
# or without pytest:
python -m unittest discover tests -v
```

**288 tests across 11 test files.** All tests run without API calls. Database-dependent tests are skipped when running without a live database but pass in full integration runs.

| File | Tests | Covers |
|------|-------|--------|
| `test_baselines.py` | ~30 | Baseline loading, JSON validity, all 19 files present |
| `test_consolidation.py` | 49 | Category inference, clustering, merging, cache, register |
| `test_trends.py` | 34 | Velocity computation, heatmap, alerts, date windows |
| `test_horizon.py` | 46 | Date parsing, RSS parsing, agenda entry parsing, persistence |
| `test_gap_analysis.py` | ~40 | Gap identification, scope mapping, profile handling |
| `test_diff.py` | ~30 | Diff detection, severity scoring, baseline-aware diffs |
| `test_learning.py` | ~25 | Feedback recording, score adjustment, keyword weights |
| `test_synthesis.py` | ~20 | Synthesis generation, conflict detection |
| `test_suite.py` | ~25 | Federal agent, PA agent |
| `test_international.py` | ~25 | EU, UK, Canada agents |
| `test_pdf.py` | ~20 | PDF extraction, metadata |

---

## Adding Coverage

**New US state:**
```python
# sources/states/new_york.py
from sources.state_agent_base import StateAgentBase

class NewYorkAgent(StateAgentBase):
    state_code     = "NY"
    state_name     = "New York"
    legiscan_state = "NY"
```
Add `"NY"` to `ENABLED_US_STATES` in `config/jurisdictions.py`.

**New country:**
```python
# sources/international/singapore.py
from sources.international.base import InternationalAgentBase

class SingaporeAgent(InternationalAgentBase):
    jurisdiction_code = "SG"
    jurisdiction_name = "Singapore"
    region            = "Asia-Pacific"

    def fetch_native(self, lookback_days=30):
        return []   # implement fetch from PDPC or equivalent
```
Add to `ENABLED_INTERNATIONAL` in `config/jurisdictions.py`.

**New baseline:**
Create a JSON file in `data/baselines/` with at minimum: `id`, `jurisdiction`, `title`, `short_name`, `status`, `overview`. Add an entry to `data/baselines/index.json`. Restart the server — no migration required.

**Manual PDF from any jurisdiction:**
Use PDF Ingest → Upload, or drop a file in `output/pdf_inbox/`. Jurisdiction is free text.

---

## Configuration (`config/keys.env`)

| Setting | Default | Description |
|---------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for AI features (summarise, diff, gap analysis, synthesis) |
| `REGULATIONS_GOV_KEY` | — | Free — Regulations.gov rulemaking dockets |
| `CONGRESS_GOV_KEY` | — | Free — Congress.gov bills + hearing schedules |
| `LEGISCAN_KEY` | — | Free — US state legislation (30k calls/month) |
| `LOOKBACK_DAYS` | `30` | Days back for document searches |
| `MIN_RELEVANCE_SCORE` | `0.5` | Minimum Claude relevance score to store a summary |
| `DB_PATH` | `./output/aris.db` | SQLite database location |
| `LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING / ERROR |

---

## After Updating Files

Any time you receive updated ARIS files, run:

```bash
python migrate.py          # adds any new tables or columns safely
cd ui && npm run build     # only needed if UI files changed
python server.py           # restart the server
```

`migrate.py` is safe to run multiple times — it skips anything already present.

---

## Design Principles

**Baselines are the starting point, documents are updates.** ARIS knows what the EU AI Act requires before any implementing act arrives. Every analysis is grounded in the settled body of law.

**Everything runs locally.** Database, cache, PDFs, learning state, all 19 baselines, velocity analytics, and the horizon calendar live on your machine. The only external calls are to government APIs (for documents) and Anthropic (for AI interpretation).

**Zero-cost features first.** You can browse 19 baselines, view the consolidation register, check regulatory velocity, and see the horizon calendar without spending a single API token. Claude calls are gated behind the keyword filter and only run on documents that pass relevance scoring.

**Full history preserved.** Every diff, gap analysis, synthesis, feedback event, and trend snapshot is stored as a new record. Nothing is overwritten.

**Graceful degradation.** Every agent wraps its calls in try/except. A failed horizon source does not block the document fetch. A failed learning call does not block summarisation. The browser UI shows a clear diagnostic when baseline files are missing rather than silently failing.
