# ARIS — AI Regulation Intelligence System

**Monitor. Baseline. Interpret. Learn. Act.**

ARIS is a fully local, agentic system that monitors AI-related legislation and regulations across US Federal agencies, US state legislatures, and international jurisdictions. It ships with 19 curated baseline regulations covering the settled body of AI law, fetches new documents from official government APIs, uses Claude to interpret and analyse them against those baselines, detects changes, learns from your feedback, synthesises cross-document intelligence, and performs company-specific compliance gap analysis — all through a browser dashboard or the command line.

Everything runs on your local machine. The 19 regulatory baselines require no API calls ever.

---

## What It Does

1. **Baselines** — ships with 19 curated, structured JSON files covering settled AI law across EU, US Federal, US states, UK, Canada, Singapore, Australia, Japan, Brazil, and international frameworks. No API calls. Always available.
2. **Fetches** — pulls new AI-related documents from official government APIs across three tracks: US Federal, US States, and International
3. **Filters** — eliminates irrelevant documents using keyword pre-screening and learned source-quality scores before any Claude API calls
4. **Interprets** — sends each document to Claude, which compares it against the baseline for its regulation family and generates plain-English summaries with requirements, action items, and urgency
5. **Detects changes** — compares new versions against their baseline and prior versions, identifying what changed, what it means, and how severe it is
6. **Learns** — adapts filtering thresholds, keyword weights, and prompt instructions based on your feedback
7. **Prioritises** — scores pending documents by urgency and processes most important ones first
8. **Synthesises** — reads across all documents on a topic and produces a regulatory landscape narrative with cross-jurisdiction conflict detection
9. **Gap analysis** — compares your company's AI systems and governance practices against baseline obligations and database documents to identify specific, document-anchored compliance gaps
10. **PDFs** — auto-downloads PDFs from Federal Register, EUR-Lex, and UK legislation; accepts manually supplied PDFs from any jurisdiction

---

## Baseline Coverage (19 baselines — no API calls)

### European Union
| Baseline | Status | What It Covers |
|----------|--------|----------------|
| EU Artificial Intelligence Act (Regulation 2024/1689) | In Force | Risk-based framework, prohibitions, high-risk AI obligations, GPAI, penalties |
| EU GDPR — AI-Relevant Provisions | In Force | Article 22 automated decisions, DPIAs, purpose limitation, data minimisation |
| EU DSA/DMA — AI Provisions | In Force | Recommender transparency, VLOP systemic risk assessment, gatekeeper ranking rules |
| EU AI Liability Directive + Product Liability Directive | Mixed | Strict liability for defective AI, rebuttable presumption of fault, evidence disclosure |

### US Federal
| Baseline | Status | What It Covers |
|----------|--------|----------------|
| Executive Order 14110 | In Force | Foundation model reporting, NIST standards direction, federal agency requirements |
| NIST AI Risk Management Framework (AI RMF 1.0) | Published | GOVERN/MAP/MEASURE/MANAGE functions, trustworthy AI characteristics |
| FTC AI Guidance and Enforcement | Active | Deceptive AI claims, algorithmic discrimination, FCRA consumer reports |
| US Sector AI Rules (CFPB, EEOC, FDA, OCC, HHS) | Active | Adverse action notices, hiring AI discrimination, SaMD clearance, model risk management |

### US States
| Baseline | Jurisdiction | Status | What It Covers |
|----------|-------------|--------|----------------|
| NYC Local Law 144 | New York City | In Force | Annual bias audits, 10-day candidate notice, public audit publication, AEDTs |
| California AI Laws (AB 2013, SB 942, etc.) | California | Multiple | Training data transparency, AI content disclosure, performer replicas |
| Illinois AI Policy Act (PA 103-0928) | Illinois | In Force | Employer AI notice, annual bias audits, anti-discrimination |
| Colorado AI Act (SB 24-205) | Colorado | In Force (Feb 2026) | High-risk AI impact assessments, human review, deployer governance |

### United Kingdom
| Baseline | Status | What It Covers |
|----------|--------|----------------|
| UK AI Regulatory Framework + ICO AI Guidance | Active | Five cross-sector principles, sector-specific regulators, UK GDPR Article 22 equivalent |

### Canada
| Baseline | Status | What It Covers |
|----------|--------|----------------|
| Canada AIDA (Bill C-27) | Proposed | High-impact AI obligations, risk assessment, incident notification (monitoring required) |

### Asia-Pacific
| Baseline | Jurisdiction | Status | What It Covers |
|----------|-------------|--------|----------------|
| Singapore Model AI Governance Framework | Singapore | Active | 11 governance areas, AI Verify toolkit, PDPA AI obligations, ASEAN guidance |
| Australia AI Governance Framework | Australia | Active | 8 ethics principles, 10 safety guardrails, Privacy Act automation obligations |
| Japan AI Guidelines | Japan | Active | METI 7 principles, APPI AI obligations, AI Safety Institute, sector-specific rules |

### Latin America
| Baseline | Jurisdiction | Status | What It Covers |
|----------|-------------|--------|----------------|
| Brazil AI (LGPD + AI Bill PL 2338/2023) | Brazil | LGPD In Force; AI Bill Advancing | LGPD Article 20, AI Bill risk classification, prohibited practices, worker rights |

### International
| Baseline | Status | What It Covers |
|----------|--------|----------------|
| OECD AI Principles + G7 Hiroshima Code of Conduct | Active | 5 OECD pillars, G7 11-point code for advanced AI, regulatory cross-reference map |

---

## Live API Sources

**US Federal** — Federal Register, Regulations.gov, Congress.gov (free API keys)

**US States** — LegiScan API (50-state coverage); Pennsylvania also uses PA General Assembly XML feed

**International** — EU (EUR-Lex SPARQL + EU AI Office RSS), UK (Parliament Bills API + legislation.gov.uk), Canada (OpenParliament + Canada Gazette RSS), Japan / China / Australia (pinned documents)

---

## Folder Structure

```
ai-reg-tracker/
│
├── main.py                              ← CLI entry point
├── server.py                            ← FastAPI REST server
├── requirements.txt
│
├── config/
│   ├── keys.env.example / keys.env      ← API keys (never commit keys.env)
│   ├── settings.py                      ← Global settings, keywords, paths
│   └── jurisdictions.py                 ← Toggle jurisdictions on/off
│
├── data/
│   └── baselines/                       ← Static baseline JSON (no API needed)
│       ├── index.json                   ← Lists all 19 baselines with metadata
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
│   ├── baseline_agent.py                ← Loads/queries baselines (no API)
│   ├── interpreter.py                   ← Claude document analysis + pre-filter
│   ├── diff_agent.py                    ← Version comparison + baseline-aware diffs
│   ├── learning_agent.py                ← Adaptive intelligence (feedback/scoring)
│   ├── orchestrator.py                  ← Coordinates all tracks + learning hooks
│   ├── scheduler.py                     ← Watch mode / recurring runs
│   ├── synthesis_agent.py               ← Cross-document synthesis + conflict detection
│   └── gap_analysis_agent.py            ← Company-profile compliance gap analysis
│
├── sources/
│   ├── federal_agent.py                 ← Federal Register, Regulations.gov, Congress.gov
│   ├── state_agent_base.py
│   ├── pdf_agent.py                     ← PDF extraction, auto-download, drop folder
│   ├── states/
│   │   └── pennsylvania.py
│   └── international/
│       ├── eu.py / uk.py / canada.py / stubs.py
│
├── utils/
│   ├── db.py                            ← All SQLite tables + CRUD (13 tables)
│   ├── cache.py
│   └── reporter.py
│
├── tests/
│   ├── test_suite.py                    ← Federal + PA agent tests
│   ├── test_international.py            ← EU, UK, Canada, stubs
│   ├── test_diff.py                     ← Diff agent + change detection
│   ├── test_learning.py                 ← Learning agent + feedback
│   ├── test_synthesis.py                ← Synthesis agent + DB
│   ├── test_pdf.py                      ← PDF agent + extraction
│   ├── test_gap_analysis.py             ← Gap analysis agent + profiles
│   └── test_baselines.py                ← Baseline agent + all 19 JSON files
│
├── ui/src/views/
│   ├── Dashboard.jsx                    ← Stats, urgency chart, recent activity
│   ├── Documents.jsx                    ← Filterable table with feedback buttons
│   ├── Changes.jsx                      ← Version diffs and addenda
│   ├── Baselines.jsx                    ← Browse all 19 baseline regulations
│   ├── Synthesis.jsx                    ← Cross-document synthesis + conflicts
│   ├── GapAnalysis.jsx                  ← Company profile + gap analysis
│   ├── PDFIngest.jsx                    ← PDF auto-download, upload, drop folder
│   ├── RunAgents.jsx                    ← On-demand pipeline execution
│   ├── Watchlist.jsx                    ← Saved keyword searches
│   ├── Graph.jsx                        ← Document relationship graph
│   ├── Learning.jsx                     ← Feedback, source quality, keyword weights
│   └── Settings.jsx                     ← API keys, jurisdictions, CLI reference
│
└── output/                              ← Created automatically
    ├── aris.db                          ← SQLite database (13 tables)
    ├── watchlist.json
    ├── pdf_inbox/                       ← Drop PDFs here for manual ingestion
    ├── pdfs/                            ← Downloaded and stored PDFs
    └── .cache/                          ← HTTP response cache (6h TTL)
```

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `documents` | Raw documents (origin: api / pdf_auto / pdf_manual) |
| `summaries` | Claude-generated summaries: requirements, action items, urgency |
| `document_diffs` | Version comparison and addendum analysis results |
| `document_links` | Explicit relationships between documents |
| `feedback_events` | Human relevance feedback driving the learning system |
| `source_profiles` | Rolling quality scores per source and agency |
| `keyword_weights` | Learned per-keyword relevance multipliers |
| `prompt_adaptations` | Claude-generated domain-specific prompt instructions |
| `fetch_history` | Fetch log for adaptive scheduling |
| `thematic_syntheses` | Cross-document synthesis and conflict detection results |
| `company_profiles` | Company profiles for gap analysis |
| `gap_analyses` | Gap analysis results (full history preserved) |
| `pdf_metadata` | PDF extraction metadata (path, pages, word count, method) |

---

## Setup

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** — needed once to build the browser UI

### 1. Install dependencies
```bash
cd ai-reg-tracker
pip install -r requirements.txt
```

### 2. Configure API keys
```bash
cp config/keys.env.example config/keys.env
# Edit keys.env
```

| Key | Source | Required? |
|-----|--------|-----------|
| `ANTHROPIC_API_KEY` | console.anthropic.com/settings/keys | **Yes** |
| `REGULATIONS_GOV_KEY` | open.gsa.gov | Recommended |
| `CONGRESS_GOV_KEY` | api.congress.gov/sign-up | Recommended |
| `LEGISCAN_KEY` | legiscan.com/legiscan | For US states |

### 3. Verify
```bash
python main.py status
```

---

## Starting the Browser UI

**Development** (hot reload):
```bash
python server.py          # Terminal 1
cd ui && npm install && npm run dev  # Terminal 2
# Open http://localhost:5173
```

**Production** (single port):
```bash
cd ui && npm install && npm run build
python server.py
# Open http://localhost:8000
```

---

## The Browser UI — Twelve Views

| View | Purpose |
|------|---------|
| **Dashboard** | Stats, urgency chart, jurisdiction breakdown, recent changes. Refreshes every 8 seconds. |
| **Documents** | Filterable table, AI summaries, feedback buttons, checklist generator, compare tool. |
| **Changes** | Version diffs and addenda with side-by-side requirement comparisons. |
| **Baselines** | Browse all 19 settled regulatory baselines. Filterable by jurisdiction. Tabs for Obligations, Prohibited practices, Timeline, Definitions, Penalties, Cross-references. Zero API calls. |
| **Synthesis** | Cross-document thematic synthesis with conflict detection. Suggested topics from your database. |
| **Gap Analysis** | Company profile editor + compliance gap analysis. Gaps anchored to specific document IDs. Posture score, roadmap, compliant areas. |
| **PDF Ingest** | Auto-download (Federal Register, EUR-Lex, UK legislation), browser upload with metadata form, drop folder ingestion. |
| **Run Agents** | On-demand pipeline execution with live log. |
| **Watchlist** | Saved keyword searches with match counts. |
| **Graph** | Force-directed document relationship graph. |
| **Learning** | Source quality charts, keyword weight drift, prompt adaptations, adaptive schedule recommendations. |
| **Settings** | API key status, enabled jurisdictions, database stats, CLI reference. |

---

## CLI Reference

```bash
# Full pipeline
python main.py run [--days N] [--limit N]

# Fetch by source
python main.py fetch [--source federal|states|international|PA|EU|GB] [--days N]

# Summarize
python main.py summarize [--limit N]

# Reports
python main.py report [--days N] [--jurisdiction X] [--urgency X]
python main.py export [--format markdown|json] [--output FILE]

# Changes
python main.py changes [--severity X] [--type X] [--unreviewed]
python main.py history DOC_ID
python main.py review DIFF_ID
python main.py diff DOC_A DOC_B
python main.py link BASE_ID ADDENDUM_ID

# Baselines (no API calls)
python main.py baselines                     # list all 19 baselines
python main.py baselines --jurisdiction EU   # filter by jurisdiction

# Synthesis
python main.py synthesis-topics              # suggested topics from your database
python main.py synthesise "topic" [-j JURS] [--no-conflicts] [--refresh]
python main.py syntheses [--limit N]

# Gap analysis
python main.py gap-profiles                  # list company profiles
python main.py gap-analyse PROFILE_ID        # run analysis
python main.py gap-analyses [--profile N]    # list results

# PDF
python main.py pdf-candidates                # documents with downloadable PDFs
python main.py pdf-download [--limit N]      # auto-download PDFs
python main.py pdf-inbox                     # list drop folder contents

# Continuous monitoring
python main.py watch [--interval N] [--days N]

# System
python main.py status
python main.py agents
```

---

## How the Baseline System Works

### What baselines contain
Each JSON file is a structured representation of a regulation's current state: overview, key definitions, obligations grouped by actor type (providers vs deployers vs both), prohibited practices with effective dates, compliance timeline with milestone dates, penalty structure, and cross-references to related regulations.

### How they integrate
**Diff agent** — before building any version-comparison prompt, the diff agent calls `BaselineAgent.format_for_diff_context()` to find the baseline matching the incoming document. The baseline is prepended to the Claude prompt so Claude can say "this change adds an obligation not present in the original Act" rather than only describing the text delta.

**Gap analysis agent** — before the scope-mapping Claude call, baseline obligations for all relevant jurisdictions are loaded and included in the prompt. This means gap analysis covers the full settled body of law even when the database has few summarised documents.

**Baselines view** — allows browsing and reference without running any analysis.

### Adding a new baseline
Create a JSON file in `data/baselines/` following the schema of any existing file, add an entry to `data/baselines/index.json`, and restart the server. No database migration, no API calls, no recompilation.

---

## How the Learning System Works

Every time you mark a document as **Not Relevant**, three things happen: the source quality score drops (Wilson confidence interval), the agency score drops separately, and matched keyword weights decrease slightly. On the next fetch, low-quality source documents need a higher composite score to pass the pre-filter — which runs locally before any Claude API call.

After 5+ false positives from the same source within 30 days, Claude automatically generates a targeted `NOTE:` instruction prepended to all future prompts for that source. View and toggle these in Learning → Adaptations.

---

## How Gap Analysis Works

**Step 1 — Create a profile.** Fill in company identity (name, industry, jurisdictions), AI systems (one entry per system: name, purpose, data types, deployment status, autonomy level), and current governance practices (seven Yes/No/Unsure checkboxes).

**Step 2 — Run the analysis.** Two Claude passes:
- **Scope mapping** — identifies which regulations apply and which specific provisions are triggered. Baseline obligations are included regardless of database state, covering the full settled body of law.
- **Gap identification** — compares applicable obligations against current practices. Each gap is anchored to a document ID, rated Critical/High/Medium/Low, shows what's required vs what exists, gives the earliest deadline, and specifies a concrete first action.

**Output** — posture score (0–100), gap cards sorted by severity, compliant areas, a three-phase roadmap, and the full scope mapping for audit purposes.

---

## Running Tests

```bash
python -m pytest tests/ -v
# or: python -m unittest tests.test_baselines -v
```

159 tests across 8 files. The `TestRealBaselineFiles` class in `test_baselines.py` validates all 19 JSON files are present, valid JSON, and contain required fields — it runs against the actual files with no mocking.

---

## Adding a New Jurisdiction

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

**New country (API source):**
```python
# sources/international/singapore.py
from sources.international.base import InternationalAgentBase

class SingaporeAgent(InternationalAgentBase):
    jurisdiction_code = "SG"
    jurisdiction_name = "Singapore"
    region            = "Asia-Pacific"
    language          = "en"

    def fetch_native(self, lookback_days=30):
        return []   # implement fetch from PDPC or equivalent
```
Add to `ENABLED_INTERNATIONAL` and `INTERNATIONAL_MODULE_MAP` in `config/jurisdictions.py`.

**New baseline (any jurisdiction):**
Create a JSON file in `data/baselines/` with at minimum: `id`, `jurisdiction`, `title`, `short_name`, `status`, `overview`. Add an entry with `doc_id_patterns` to `data/baselines/index.json`. Restart the server.

**Manual PDF from any jurisdiction:**
Use PDF Ingest → Upload tab or drop a file in `output/pdf_inbox/`. Jurisdiction is free text — any country or region is supported.

---

## Configuration

Edit `config/keys.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for all AI features |
| `REGULATIONS_GOV_KEY` | — | Regulations.gov API |
| `CONGRESS_GOV_KEY` | — | Congress.gov API |
| `LEGISCAN_KEY` | — | US state monitoring |
| `LOOKBACK_DAYS` | `30` | Days back for new documents |
| `MIN_RELEVANCE_SCORE` | `0.5` | Minimum Claude relevance score |
| `DB_PATH` | `./output/aris.db` | SQLite database path |
| `CACHE_TTL_HOURS` | `6` | HTTP response cache TTL |
| `LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING / ERROR |

---

## Design Principles

**Baselines are the starting point, documents are updates.** The system knows what the EU AI Act requires before any implementing act arrives. New documents are analysed against that baseline, not in isolation.

**Every gap links to a document.** The gap analysis never produces generic advice. Every identified gap includes a `document_id` traceable in the Documents view.

**Everything runs locally.** Database, cache, PDFs, learning state, and all 19 baselines live on your machine.

**The browser UI is additive.** Every feature is accessible from the CLI. FastAPI is a thin REST layer over the same Python agents.

**Learning never blocks operation.** All learning calls are wrapped in try/except with graceful fallback.

**Full history preserved.** Every diff, gap analysis, synthesis, and feedback event is stored as a new record. Nothing is overwritten.
