# ARIS — Automated Regulatory Intelligence System

**Monitor. Baseline. Compare. Interpret. Consolidate. Trend. Horizon. Learn. Act.**

ARIS is a fully local, agentic system that monitors **AI regulation and data privacy law** across US Federal agencies, US state legislatures, and international jurisdictions. It ships with 31 curated baseline regulations, fetches live documents from official government APIs, uses Claude to interpret and analyse them, detects changes, tracks regulatory velocity, scans the regulatory horizon for planned regulations, consolidates obligations across all sources, compares jurisdictions side-by-side, and performs company-specific compliance gap analysis — all through a browser dashboard or the command line.

Everything runs on your machine. The 31 baseline regulations, consolidation register, velocity analytics, and horizon calendar require no Claude API calls.

---

## What It Does

| # | Feature | API Calls | Description |
|---|---------|-----------|-------------|
| 1 | **Baselines** | None | 31 curated baselines covering settled AI regulation and data privacy law. Always available. |
| 2 | **Fetch** | None | Pulls documents from Federal Register, Regulations.gov, Congress.gov, EUR-Lex, UK Parliament, Canada, and state legislatures. |
| 3 | **Filter** | None | Keyword pre-screening with domain-aware scoring (AI vs privacy vocabulary). Skipped documents are recorded with reasons — visible in the Documents view. |
| 4 | **Interpret** | Claude | Plain-English summaries, urgency ratings, requirements, action items, deadlines. Domain-specific prompts for AI regulation vs data privacy. |
| 5 | **Change detection** | Claude | Baseline-aware diffs — compares new documents against the settled baseline, not just against each other. |
| 6 | **Consolidation** | Optional | De-duplicated obligation register from all 31 baselines. Fast mode: zero API calls. Full mode: one Claude call, cached 24h. |
| 7 | **Trends & velocity** | None | Jurisdiction velocity sparklines, impact-area heatmap, acceleration alerts — computed from your database, no API calls. |
| 8 | **Horizon scanning** | None | Monitors Unified Regulatory Agenda, congressional hearings, EU Work Programme, and UK Parliament upcoming business. |
| 9 | **Compare** | Claude | Side-by-side structured comparison of any two baselines — divergences, agreements, strictness, practical notes. |
| 10 | **Synthesis** | Claude | Cross-document regulatory landscape with conflict detection. |
| 11 | **Gap analysis** | Claude | Company-profile compliance gaps anchored to specific document IDs with phased roadmap. |
| 12 | **Document review** | None | Feedback marks documents Relevant / Partially Relevant / Not Relevant. Not-relevant documents move to an archive. |
| 13 | **Learning** | Claude (periodic) | Adapts keyword weights, source-quality scores, and prompt instructions from your feedback. Domain-aware: AI and privacy sources scored separately. |
| 14 | **PDFs** | None | Auto-download PDFs from Federal Register, EUR-Lex, UK legislation; accept manually supplied PDFs. |

---

## Browser Views

| View | What It Shows |
|------|---------------|
| **Dashboard** | Alert rail (critical changes, upcoming deadlines), regulatory pulse (velocity sparklines), system health tiles |
| **Documents** | Active document list with domain filter, review badges, Skipped indicator with reason; Archive tab |
| **Changes** | Keyword search, version diffs with severity badges and side-by-side requirement comparisons |
| **Baselines** | Domain tabs (AI Regulation / Data Privacy), jurisdiction filter, obligations and prohibitions |
| **Compare** | Side-by-side Claude analysis of any two regulations — divergences, agreements, strictness by topic, practical notes |
| **Trends** | Jurisdiction velocity sparklines with domain filter, impact-area heatmap, acceleration alerts |
| **Horizon** | 12-month forward calendar with domain filter, timeline/list views |
| **Obligations** | Standalone obligation register — browse consolidated obligations across any jurisdiction set |
| **Ask ARIS** | RAG-powered Q&A across all documents with inline citations |
| **Briefs** | One-page regulatory briefs per jurisdiction |
| **Synthesis** | Cross-jurisdiction regulatory narratives and conflict maps |
| **Gap Analysis** | Company profiles, domain-scoped gap analysis, obligation register, phased roadmap |
| **Enforcement** | FTC, SEC, CFPB, ICO enforcement actions and federal litigation |
| **Graph** | Document relationship network |
| **Concept Map** | Cross-jurisdiction concept analysis |
| **Timeline** | Chronological regulatory timeline |
| **Watchlist** | Keyword-based alerts across all documents |
| **PDF Ingest** | Upload PDFs or trigger auto-download |
| **Run Agents** | Trigger fetch/summarise with live log; Force Summarize bypasses pre-filter |
| **Learning** | Source quality profiles, keyword weights, prompt adaptations, feedback history |
| **Settings** | API key status with impact descriptions, jurisdiction toggles, database stats |

---

## Dual-Domain Architecture

ARIS monitors two distinct regulatory domains that share infrastructure but have separate vocabularies, prompts, baselines, and scoring:

**AI Regulation** — legislation and guidance governing the development, deployment, and use of AI systems. Risk classification, transparency, oversight, prohibited uses, conformity assessment.

**Data Privacy** — laws governing the collection, processing, and transfer of personal data. Consent, individual rights, breach notification, legal bases, international transfers.

Every document, summary, change, and horizon item carries a `domain` field (`ai` | `privacy` | `both`). Every data view has a three-pill domain filter (All / AI Regulation / Data Privacy) that is independent and persisted per view — Documents can be filtered to Privacy while Changes shows All. The domain filter on Run Agents defaults to the most recently used domain across all views.

### Domain keyword scoring

AI documents are scored using AI-vocabulary keyword matching. Privacy documents are scored using a separate `is_privacy_relevant()` function against ~130 privacy terms. Documents in the wrong scoring track were previously silently filtered; they now receive a `Skipped` stub with the reason visible in the Documents view.

---

## Baseline Coverage (31 baselines — no API calls required)

### AI Regulation (19 baselines)

| Jurisdiction | Baseline | Status |
|-------------|----------|--------|
| EU | EU AI Act (Regulation 2024/1689) | In Force |
| EU | EU GDPR — AI Provisions (Article 22) | In Force |
| EU | EU DSA/DMA — AI Provisions | In Force |
| EU | EU AI Liability + Product Liability Directives | Mixed |
| Federal | Executive Order 14110 | In Force |
| Federal | NIST AI RMF 1.0 | Published |
| Federal | FTC AI Guidance | Active |
| Federal | US Sector AI Rules (CFPB, EEOC, FDA, OCC) | Active |
| GB | UK AI Framework + ICO AI Guidance | Active |
| CA_STATE | California AI Laws | Multiple |
| CO | Colorado AI Act | In Force (Feb 2026) |
| IL | Illinois AI Policy Act | In Force |
| NY | NYC Local Law 144 | In Force |
| CA | Canada AIDA (Bill C-27) | Proposed |
| JP | Japan AI Guidelines | Active |
| AU | Australia AI Governance Framework | Active |
| BR | Brazil AI (LGPD + PL 2338/2023) | Mixed |
| SG | Singapore AI Governance Framework | Active |
| INTL | OECD AI Principles + G7 Hiroshima Code | Active |

### Data Privacy (12 baselines)

| Jurisdiction | Baseline | Status |
|-------------|----------|--------|
| EU | GDPR (full) | In Force |
| EU | EU Data Act | In Force |
| EU | ePrivacy / Cookie Law | In Force |
| GB | UK GDPR / DPA 2018 | In Force |
| CA_STATE | CCPA / CPRA | In Force |
| Federal | US State Privacy Laws (consolidated) | Multiple |
| Federal | US Federal Privacy (HIPAA, COPPA, GLBA, FERPA) | In Force |
| CA | PIPEDA / CPPA (Bill C-27) | Mixed |
| BR | LGPD | In Force |
| JP | Japan APPI | In Force |
| AU | Australia Privacy Act | In Force |
| SG | Singapore PDPA | In Force |

---

## Live API Sources

**US Federal** — Federal Register, Regulations.gov, Congress.gov (free API keys required)

**US States** — LegiScan API (50-state coverage, free key required). Pennsylvania additionally uses the PA General Assembly ZIP archive (`palegis.us/data/bill-history/YEAR.zip`, updated hourly, no key needed).

**International** — EU (EUR-Lex SPARQL + EU AI Office RSS), UK (Parliament Bills API + legislation.gov.uk), Canada (OpenParliament + Canada Gazette RSS)

**Enforcement** — FTC, SEC, CFPB, EEOC, DOJ press releases; ICO enforcement (UK); CourtListener federal courts (optional key)

**Horizon** — Unified Regulatory Agenda (no key), Congress.gov hearing schedules, EU Commission Work Programme (no key), UK Parliament whatson API (no key)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pdfplumber pypdf   # optional, for PDF extraction

# 2. Configure API keys
cp config/keys.env.example config/keys.env   # Mac/Linux
# copy config\keys.env.example config\keys.env   # Windows
# Edit config/keys.env — at minimum set ANTHROPIC_API_KEY

# 3. Run database migration
python migrate.py

# 4. Build the UI (requires Node.js 18+)
cd ui && npm install && npm run build && cd ..

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
python main.py run                              # fetch all sources + summarise
python main.py run --domain both                # explicit: both AI and privacy
python main.py run --domain ai                  # AI regulation only
python main.py run --domain privacy             # data privacy only
python main.py fetch                            # fetch only (no Claude)
python main.py fetch --source federal           # federal | states | international | horizon
python main.py fetch --days 90                  # longer lookback window
python main.py summarize                        # summarise pending documents
python main.py summarize --force                # bypass pre-filter (clears Skipped docs)
python main.py summarize --limit 10

# ── Baselines (no API calls) ──────────────────────────────────────────────────
python main.py baselines                        # list all 31 baselines
python main.py baselines --jurisdiction EU

# ── Changes ───────────────────────────────────────────────────────────────────
python main.py changes [--severity Critical] [--unreviewed]
python main.py diff DOC_A DOC_B

# ── Comparison ────────────────────────────────────────────────────────────────
# Via the browser: Research → Compare
# Or via API: POST /api/compare {"source_id_a": "eu_ai_act", "source_id_b": "eu_gdpr_full", "focus": "automated decision-making"}

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
python main.py watch [--interval 24]            # run every N hours continuously

# ── System ────────────────────────────────────────────────────────────────────
python main.py status
python migrate.py                               # safe to re-run; adds missing columns
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
│   ├── settings.py                  ← Global settings, keywords, ACTIVE_DOMAINS
│   └── jurisdictions.py             ← Toggle which jurisdictions are monitored
│
├── data/
│   └── baselines/                   ← 31 static JSON baseline files (no API)
│       ├── index.json
│       ├── [19 AI regulation baselines]
│       └── [12 data privacy baselines]
│
├── agents/
│   ├── baseline_agent.py            ← Loads and queries baselines (domain-aware)
│   ├── compare_agent.py             ← Side-by-side regulation comparison
│   ├── consolidation_agent.py       ← De-duplicated obligation register
│   ├── diff_agent.py                ← Baseline-aware version comparison
│   ├── gap_analysis_agent.py        ← Company-profile compliance gap analysis
│   ├── interpreter.py               ← Claude analysis + domain-aware pre-filter
│   ├── learning_agent.py            ← Adaptive scoring (domain-aware)
│   ├── orchestrator.py              ← Coordinates all fetch and analysis tracks
│   ├── scheduler.py                 ← Watch mode / recurring runs
│   ├── synthesis_agent.py           ← Cross-document synthesis
│   └── trend_agent.py               ← Velocity analytics, heatmap (no API)
│
├── sources/
│   ├── enforcement_agent.py         ← FTC, SEC, CFPB, ICO, CourtListener
│   ├── federal_agent.py             ← Federal Register, Regulations.gov, Congress.gov
│   ├── horizon_agent.py             ← Regulatory horizon scanning
│   ├── pdf_agent.py                 ← PDF extraction and auto-download
│   ├── state_agent_base.py          ← LegiScan + native XML base class
│   ├── states/
│   │   ├── pennsylvania.py          ← PA ZIP archive (palegis.us, hourly)
│   │   ├── virginia.py
│   │   ├── colorado.py
│   │   ├── illinois.py
│   │   └── california.py
│   └── international/
│       ├── eu.py
│       ├── uk.py
│       ├── canada.py
│       └── stubs.py
│
├── utils/
│   ├── db.py                        ← SQLite (17 tables, domain column on 4 tables)
│   ├── cache.py                     ← HTTP cache, keyword scoring, is_privacy_relevant()
│   ├── llm.py                       ← LLM abstraction layer
│   ├── rag.py                       ← RAG passage index for Ask ARIS
│   ├── search.py                    ← Full-text search + PRIVACY_TERMS_EXPANDED
│   └── reporter.py
│
├── tests/                           ← 636 tests across 18 files
│   ├── test_suite.py                ← Federal + PA agent
│   ├── test_international.py        ← EU, UK, Canada
│   ├── test_diff.py                 ← Diff agent + change detection
│   ├── test_learning.py             ← Learning agent + feedback
│   ├── test_synthesis.py            ← Synthesis agent
│   ├── test_pdf.py                  ← PDF extraction
│   ├── test_gap_analysis.py         ← Gap analysis agent
│   ├── test_baselines.py            ← All 31 baseline files
│   ├── test_consolidation.py        ← Consolidation agent
│   ├── test_trends.py               ← Trend/velocity agent
│   ├── test_horizon.py              ← Horizon scanning
│   ├── test_search.py               ← Full-text search
│   ├── test_qa.py                   ← Q&A / RAG
│   ├── test_graph.py                ← Knowledge graph
│   ├── test_concepts.py             ← Concept mapping
│   ├── test_intelligence.py         ← Intelligence / brief agent
│   ├── test_enforcement.py          ← Enforcement agent
│   └── test_domain_foundation.py   ← Privacy domain taxonomy + scoring
│
└── ui/src/views/
    ├── Dashboard.jsx                ← Alert rail, regulatory pulse, system health
    ├── Documents.jsx                ← Active/Archive tabs, Skipped indicator
    ├── Changes.jsx                  ← Keyword search, version diffs
    ├── Baselines.jsx                ← Domain tabs, jurisdiction filter
    ├── Compare.jsx                  ← Side-by-side regulation comparison
    ├── Trends.jsx                   ← Velocity sparklines, heatmap, alerts
    ├── Horizon.jsx                  ← Forward calendar with domain filter
    ├── ObligationRegister.jsx       ← Standalone obligation register
    ├── AskAris.jsx                  ← RAG Q&A with citations
    ├── Brief.jsx                    ← One-page jurisdiction briefs
    ├── Synthesis.jsx                ← Cross-document narratives
    ├── GapAnalysis.jsx              ← Profiles, domain-scoped gaps, roadmap
    ├── Enforcement.jsx              ← FTC/SEC/ICO enforcement actions
    ├── Graph.jsx
    ├── ConceptMap.jsx
    ├── Timeline.jsx
    ├── Watchlist.jsx
    ├── PDFIngest.jsx
    ├── RunAgents.jsx                ← Live log, Force Summarize option
    ├── Learning.jsx
    └── Settings.jsx                 ← Key impact descriptions, domain-aware stats
```

---

## Database Tables (17 tables)

| Table | Purpose |
|-------|---------|
| `documents` | Raw documents fetched from sources. Has `domain` column (`ai`/`privacy`/`both`). |
| `summaries` | Claude-generated summaries. `urgency='Skipped'` marks pre-filter rejections with reason. |
| `document_diffs` | Version comparisons with severity and requirement changes. Has `domain` column. |
| `document_links` | Relationships between documents (supersedes, amends, clarifies). |
| `pdf_metadata` | PDF extraction records. |
| `feedback_events` | Human relevance feedback (relevant / not_relevant / partially_relevant). |
| `source_profiles` | Rolling quality scores per source and agency. |
| `keyword_weights` | Learned keyword multipliers from feedback. |
| `prompt_adaptations` | Claude-generated prompt notes for problematic sources. |
| `fetch_history` | Fetch run log. |
| `thematic_syntheses` | Cross-document synthesis results. |
| `company_profiles` | Company profiles for gap analysis. |
| `gap_analyses` | Gap analysis results (history preserved). |
| `regulatory_horizon` | Forward-looking horizon items. Has `domain` column. |
| `trend_snapshots` | Cached velocity / heatmap / alert data. |
| `obligation_register_cache` | Cached consolidation register results. |
| `knowledge_graph_edges` | Document relationship graph edges. |

---

## Key Concepts

### Pending vs Skipped documents

Documents that fail the relevance pre-filter no longer stay permanently in the pending queue. Instead, a stub summary with `urgency='Skipped'` is written, and the skip reason appears in the Documents view (e.g. "pre-filter score 0.03 below threshold 0.08"). To process skipped documents regardless of score, use **Force Summarize** in Run Agents or `python main.py summarize --force`.

### Domain system

`ACTIVE_DOMAINS` in `config/keys.env` controls which domains are fetched (default: `both`). The CLI `--domain` flag overrides per-run. All four primary database tables carry a `domain` column so filtering is cheap. The domain filter in each UI view is stored independently in `localStorage` (e.g. `aris_domain_documents`, `aris_domain_changes`) so each view remembers its own setting.

### Jurisdiction comparison

`POST /api/compare` accepts two baseline or document IDs plus an optional focus topic. The `CompareAgent` loads both sources, extracts the most relevant sections (with focus filtering), and sends a single Claude call that returns structured divergences, agreements, strictness comparison by topic, and practical notes for organisations subject to both frameworks. Results are rendered in the Compare view with collapsible side-by-side cards per divergence area. 12 suggested comparison pairs are pre-loaded on the placeholder screen.

### Obligation Register

The `ConsolidationAgent` produces a de-duplicated list of what must actually be done across a set of jurisdictions. Accessible as a standalone top-level view (Research → Obligations) or embedded inside Gap Analysis results. Two modes:

- **Fast** (no API) — structural consolidation from baselines using fuzzy title matching and keyword category assignment. Under 100ms.
- **Full** (one Claude call, cached 24h) — semantic deduplication catches near-identical obligations phrased differently across jurisdictions.

Each entry: action-verb title, category, description, strictest scope, source list, earliest deadline, universality (Universal / Majority / Single).

### Four Fetch Tracks

**Track 1 — US Federal:** Federal Register rules, proposed rules, and notices. Regulations.gov dockets. Congress.gov bills. Both AI and privacy terms searched.

**Track 2 — US States:** LegiScan 50-state API with AI + privacy keyword search. Pennsylvania additionally uses the PA General Assembly ZIP archive (`palegis.us/data/bill-history/YEAR.zip`, updated hourly Monday–Friday, no key needed).

**Track 3 — International:** EUR-Lex SPARQL for EU legislation. UK Parliament Bills API. OpenParliament and Canada Gazette for Canada. Japan, Australia, Singapore, Brazil via configured stubs.

**Track 4 — Horizon:** Unified Regulatory Agenda, congressional committee hearing schedules, EU Commission Work Programme, UK Parliament upcoming bill stages. No additional API keys required.

### Dashboard — alert-first design

The dashboard answers "what needs my attention right now?" rather than listing documents. It renders three zones:

1. **Alert rail** — only renders when something is actionable: unreviewed critical changes, upcoming horizon deadlines within 30 days, critical-urgency documents, large pending summarisation backlog. When everything is clear, a single green confirmation line renders instead.
2. **Insight grid** — regulatory pulse (velocity sparklines per jurisdiction with trend arrows and acceleration alerts) + coverage/deadline/enforcement summary panels.
3. **System health** — data coverage %, domain split, baselines loaded, API key status with red border if the Anthropic key is missing.

---

## Running Tests

```bash
python -m pytest tests/ -v
# or without pytest:
python -m unittest discover tests -v
```

**636 tests across 18 test files.** All tests run without live API calls. Database-dependent tests are skipped unless a live database is present.

| File | Covers |
|------|--------|
| `test_suite.py` | Federal agent, PA agent (ZIP feed, URL format) |
| `test_international.py` | EU, UK, Canada agents |
| `test_baselines.py` | All 31 baseline files — JSON validity, required fields, domain tags |
| `test_consolidation.py` | Category inference, clustering, merging, cache, register structure |
| `test_trends.py` | Velocity computation, heatmap, alerts, date windows |
| `test_horizon.py` | Date parsing, RSS parsing, agenda entry parsing, persistence |
| `test_gap_analysis.py` | Gap identification, scope mapping, profile handling |
| `test_diff.py` | Diff detection, severity scoring, baseline-aware diffs |
| `test_learning.py` | Feedback recording, score adjustment, keyword weights |
| `test_synthesis.py` | Synthesis generation, conflict detection |
| `test_search.py` | Full-text search and ranking |
| `test_qa.py` | Q&A RAG pipeline |
| `test_graph.py` | Knowledge graph edges |
| `test_concepts.py` | Concept mapping |
| `test_intelligence.py` | Brief generation |
| `test_enforcement.py` | Enforcement agent — FTC, ICO, domain detection |
| `test_pdf.py` | PDF extraction and metadata |
| `test_domain_foundation.py` | Privacy taxonomy, `is_privacy_relevant()`, domain detection, 57 tests |

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
# sources/international/south_korea.py
from sources.international.base import InternationalAgentBase

class SouthKoreaAgent(InternationalAgentBase):
    jurisdiction_code = "KR"
    jurisdiction_name = "South Korea"
    region            = "Asia-Pacific"

    def fetch_native(self, lookback_days=30):
        return []   # implement PIPC / ISMS-P feed
```
Add to `ENABLED_INTERNATIONAL` in `config/jurisdictions.py`.

**New baseline:**
Create a JSON file in `data/baselines/` with at minimum: `id`, `jurisdiction`, `title`, `short_name`, `status`, `overview`, `domain` (`ai` or `privacy`). Add an entry to `data/baselines/index.json`. Restart the server — no migration required.

**Manual PDF:**
Use PDF Ingest → Upload, or drop a file in `output/pdf_inbox/`. Jurisdiction is free text.

---

## Configuration (`config/keys.env`)

| Setting | Default | Description |
|---------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for all AI features (summarise, diff, gap, synthesis, compare) |
| `REGULATIONS_GOV_KEY` | — | Free — federal rulemaking dockets |
| `CONGRESS_GOV_KEY` | — | Free — US bills and hearing schedules |
| `LEGISCAN_KEY` | — | Free — all US state legislation |
| `COURTLISTENER_KEY` | — | Optional — federal court opinions and litigation |
| `ACTIVE_DOMAINS` | `both` | `ai` / `privacy` / `both` — which regulatory domains to fetch |
| `LOOKBACK_DAYS` | `30` | Days back for document searches |
| `DB_PATH` | `./output/aris.db` | SQLite database location |
| `LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING / ERROR |

---

## After Updating Files

Any time you receive updated ARIS files:

```bash
python migrate.py          # adds any new tables or columns safely
cd ui && npm run build     # only if UI files changed
python server.py           # restart the server
```

`migrate.py` is safe to run multiple times — it skips anything already present.

---

## Design Principles

**Baselines are the starting point, documents are updates.** ARIS knows what the EU AI Act requires and what GDPR demands before any implementing act or enforcement decision arrives. Every analysis is grounded in the settled body of law.

**Two domains, one system.** AI regulation and data privacy share infrastructure but have separate vocabularies, scoring functions, and LLM prompts. A GDPR breach notification article won't be silently dropped by an AI-keyword filter.

**Everything runs locally.** Database, cache, PDFs, learning state, all 31 baselines, velocity analytics, and the horizon calendar live on your machine. The only external calls are to government APIs (for documents) and Anthropic (for AI interpretation).

**Zero-cost features first.** You can browse 31 baselines, view the consolidation register, check regulatory velocity, and see the horizon calendar without spending a single API token. Claude calls are gated behind the relevance filter and only run on documents that pass scoring.

**Transparency over silence.** Documents rejected by the pre-filter are recorded as `Skipped` with the reason visible in the UI, not silently dropped. API key status in Settings shows exactly which features each missing key disables.

**Full history preserved.** Every diff, gap analysis, synthesis, feedback event, and trend snapshot is stored as a new record. Nothing is overwritten.

**Graceful degradation.** Every agent wraps its calls in try/except. A failed state source does not block the federal fetch. A failed horizon source does not block document fetching. The UI shows clear diagnostics rather than silently failing.
