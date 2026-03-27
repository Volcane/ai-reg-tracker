# ARIS — Automated Regulatory Intelligence System

**Monitor. Baseline. Compare. Interpret. Consolidate. Trend. Horizon. Enforce. Learn. Act.**

ARIS is a fully local, agentic system that monitors **AI regulation and data privacy law** across all 50 US states, 10 international jurisdictions, and US Federal agencies. It ships with 32 curated baseline regulations, fetches live documents from official government APIs and enforcement feeds, uses Claude to interpret and analyse them, detects changes, tracks regulatory velocity, scans the regulatory horizon for planned regulations, consolidates obligations, compares jurisdictions side-by-side, and performs company-specific compliance gap analysis — all through a browser dashboard or the command line.

Everything runs on your machine. No SaaS subscription, no data leaving your environment, no per-query costs beyond your own API key.

---

## License

ARIS is licensed under the **Elastic License 2.0 (ELv2)**. You may use, copy, and modify it for personal, educational, and non-commercial purposes. You may not sell it, offer it as a commercial product or service, or use it as the basis of a paid product without express written permission. See [LICENSE](LICENSE) for the full terms.

Copyright (c) 2026 Mitch Kwiatkowski

**Disclaimer:** ARIS is an informational research tool only. Nothing it produces constitutes legal, compliance, or regulatory advice. Always consult qualified legal counsel before making compliance decisions.

---

## What It Does

| # | Feature | API Calls | Description |
|---|---------|-----------|-------------|
| 1 | **Baselines** | None | 32 curated baselines covering settled AI regulation and data privacy law. Always available offline. |
| 2 | **Fetch** | None | Concurrent fetch from all 50 US states, 10 international jurisdictions, and 5 US Federal sources. |
| 3 | **Filter** | None | Domain-aware keyword pre-screening (150+ terms) with false-positive protection. Skipped docs recorded with reason. |
| 4 | **Interpret** | Claude | Plain-English summaries, urgency ratings, requirements, action items, deadlines. Domain-specific prompts. |
| 5 | **Change detection** | Claude | Baseline-aware diffs — compares new documents against settled law, not just prior versions. |
| 6 | **Consolidation** | Optional | De-duplicated obligation register from all 32 baselines. Fast mode: zero API calls. Full mode: one Claude call. |
| 7 | **Trends & velocity** | None | Jurisdiction velocity chart (rolling 12-month window), impact-area heatmap, acceleration alerts. |
| 8 | **Horizon scanning** | None | Unified Regulatory Agenda, congressional hearings, EU Work Programme, UK Parliament, plus seeded upcoming events. |
| 9 | **Compare** | Claude | Side-by-side structured comparison of any two of the 32 baselines. |
| 10 | **Synthesis** | Claude | Cross-document regulatory landscape with conflict detection. Export to .docx. |
| 11 | **Gap analysis** | Claude | Company-profile compliance gaps, phased roadmap. Export to .docx. |
| 12 | **Enforcement** | None | 10 live sources: FTC, SEC, CFPB, EEOC, DOJ, ICO (UK), CourtListener, Google News, Regulatory Oversight, Courthouse News. Story grouping deduplicates coverage. |
| 13 | **Document review** | None | Feedback marks documents Relevant / Partially Relevant / Not Relevant. |
| 14 | **Autonomous learning** | Claude (periodic) | Every processed document feeds the relevance model. False-positive sources are down-weighted automatically. Documents Claude scores ≤ 0.15 auto-archive. |
| 15 | **PDFs** | None | Auto-download PDFs from Federal Register, EUR-Lex, UK legislation; accept manual uploads. |
| 16 | **Notifications** | None | Email (SMTP) and Slack webhook digests on critical findings and scheduled runs. |
| 17 | **Scheduled monitoring** | None | Background scheduler with configurable interval, domain, and lookback. Survives restarts. |

---

## Browser Views

| View | What It Shows |
|------|---------------|
| **Dashboard** | Alert rail, pulse sparklines, horizon widget (urgency buckets + countdown list), recent enforcement, system health |
| **Documents** | Active document list with sort (date fetched / published / urgency / jurisdiction), domain filter, review badges |
| **Changes** | Unreviewed change cards with document titles, severity badges, keyword search, side-by-side diffs |
| **Baselines** | Domain tabs (AI Regulation / Data Privacy), jurisdiction filter, obligations and prohibitions |
| **Compare** | Side-by-side Claude analysis of any two of 32 baselines |
| **Trends** | Jurisdiction velocity chart (rolling 12-month window ending today), impact-area heatmap, acceleration alerts |
| **Horizon** | 12-month forward calendar with domain filter — deadlines, proposed rules, hearings |
| **Obligations** | De-duplicated obligation register across any jurisdiction set |
| **Ask ARIS** | RAG-powered Q&A across all documents and baselines with citations |
| **Briefs** | One-page regulatory briefs per jurisdiction |
| **Synthesis** | Cross-jurisdiction narratives, conflict maps, .docx export |
| **Gap Analysis** | Company profiles, domain-scoped gap cards, roadmap, .docx export |
| **Enforcement** | 10 enforcement sources with story grouping — collapses multiple articles about the same case into one expandable card |
| **Graph** | Document relationship network |
| **Concept Map** | Cross-jurisdiction concept analysis |
| **Timeline** | Chronological regulatory timeline |
| **Watchlist** | Keyword-based alerts with domain filter |
| **PDF Ingest** | Upload PDFs or trigger auto-download |
| **Run Agents** | Trigger fetch/summarise with compact 50-state regional grid; first-run banner; post-run summary |
| **Learning** | Source quality profiles, keyword weights, prompt adaptations |
| **Settings** | API keys, jurisdiction toggles, scheduled monitoring, notifications |

---

## Coverage

### US States (50)

All 50 states monitored via LegiScan API. Ten states also have native legislative feeds:

| Tier | States | Source |
|------|--------|--------|
| **Native + LegiScan** | PA, CA, CO, IL, TX, WA, NY, FL, MN, CT | State-specific XML/API feeds + LegiScan |
| **Active pipeline** | VA, NJ, MA, OR, MD, GA, AZ, NC, MI, OH, NV, UT, IN, TN, KY, SC, WI, MO | LegiScan |
| **Emerging activity** | LA, AL, MS, AR, IA, KS, NE, NM, OK, WV, ID, MT, ND, SD, WY, AK, HI, ME, NH, VT, RI, DE | LegiScan |

**Notable enacted state laws:**

| State | Law | Status |
|-------|-----|--------|
| Texas | TRAIGA — AI risk management | In force Jan 2026 |
| Colorado | AI Act SB 24-205 — high-risk AI | Effective Jun 2026 |
| Illinois | AIPA — automated employment decisions | Enacted |
| Utah | Utah AI Policy Act | Enacted 2024 |
| California | 24+ AI laws including SB 53, AB 2013, SB 942 | Various |
| Montana | Consumer Data Privacy Act | In force 2024 |
| Iowa | Consumer Data Protection Act | In force 2025 |
| Nebraska | Data Privacy Act | In force 2025 |
| Delaware | Personal Data Privacy Act | In force 2025 |
| Indiana | Consumer Data Protection Act | In force 2026 |

> **LegiScan quota:** The free tier allows ~30 API calls/day. Fetching all 50 states uses 50+ calls. Run states in regional batches using the Run Agents grid, or use `python diagnose_legiscan.py` to check quota status before a full run.

### International (10)

| Jurisdiction | Primary Source | Key Instruments |
|-------------|----------------|-----------------|
| European Union | EUR-Lex SPARQL + EU AI Office RSS | EU AI Act, GDPR, Data Act, DSA/DMA |
| United Kingdom | Parliament Bills API + legislation.gov.uk | UK GDPR/DPA 2018, AI Framework |
| Canada | OpenParliament + Canada Gazette + ISED | PIPEDA, CPPA (Bill C-27), AIDA |
| Singapore | PDPC RSS + IMDA RSS | Model AI Governance Framework, PDPA |
| India | PIB RSS (MEITY) | DPDP Act 2023, IndiaAI Mission |
| Brazil | ANPD RSS + Senate RSS | LGPD, AI Bill PL 2338/2023 |
| Japan | METI RSS + Google News fallback | AI Promotion Act (May 2025), AI Guidelines v1.1 |
| South Korea | MSIT press releases | PIPA 2023 amendments, AI Promotion Act |
| Australia | Federal Register API + pinned docs | AI Safety Standard, Privacy Act review |
| China | Pinned documents | Generative AI Interim Measures, Algorithm Recommendation Regulation |

### Enforcement Sources (10)

| Source | Coverage |
|--------|----------|
| FTC | Press releases — algorithmic bias, AI fraud, dark patterns |
| SEC | EDGAR search — AI fraud, algorithmic manipulation |
| CFPB | Newsroom — automated underwriting, credit scoring |
| EEOC | Newsroom — employment AI discrimination |
| DOJ | Press releases — civil rights AI discrimination |
| ICO (UK) | Media centre — GDPR / data protection enforcement |
| CourtListener | Federal court opinions and dockets (PACER/RECAP) |
| Google News | 7 targeted queries: AI lawsuits, data privacy fines, state AG enforcement, social media verdicts |
| Regulatory Oversight | Troutman Pepper enforcement blog — state AG and FTC actions |
| Courthouse News | State and federal court filings the day they are filed |

The Enforcement view groups articles about the same story (e.g. 28 articles about the Meta/YouTube social media addiction verdict) into a single expandable card with a "N more articles" toggle.

---

## Dual-Domain Architecture

ARIS monitors two distinct regulatory domains with separate vocabularies, prompts, baselines, and scoring:

- **AI Regulation** — risk classification, transparency, oversight, prohibited uses, conformity assessment
- **Data Privacy** — consent, individual rights, breach notification, legal bases, international transfers

Every document, summary, change, and horizon item carries a `domain` field (`ai` | `privacy` | `both`). Every view has a three-pill domain filter persisted independently per view.

### Relevance Filtering (150+ Terms)

1. **Strong-signal fast path** — unambiguous AI terms ("artificial intelligence", "automated decision", "deepfake") pass immediately
2. **Known false-positive guard** — blocks NAIC, MAID, PAID leave, BRAIN Initiative unless 2+ additional AI terms are present
3. **Scored match** — 150+ term taxonomy; ambiguous terms only count when backed by at least one unambiguous AI term

Pre-filter validation runs against the **bill title only** — not `title + search_keyword` — preventing LegiScan result contamination.

---

## Autonomous Learning

ARIS improves its own relevance filtering without user input:

- **Skipped stubs feed the learner** — all three skip gates return a stub that calls `record_auto_feedback()` with the relevance score as signal
- **Auto-archive** — documents Claude rates ≤ 0.15 automatically move to Archive
- **Domain-keyed profiles** — AI and privacy sources accrue quality scores independently
- **Summarization guard** — Skipped documents are excluded from re-summarization on normal runs; Force Summarize re-includes them for one pass

---

## Regulatory Horizon

Key upcoming dates (as of March 2026):

| Event | Date |
|-------|------|
| Colorado AI Act enforcement effective | Jun 30, 2026 |
| EU AI Act — GPAI obligations apply | Aug 2, 2026 |
| California SB 942 (AI transparency) effective | Aug 2, 2026 |
| EU Data Act fully applicable | Sep 12, 2026 |
| EU AI Act — High-Risk AI obligations | Aug 2, 2027 |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pdfplumber pypdf   # optional, for PDF extraction

# 2. Configure API keys
cp config/keys.env.example config/keys.env
# Edit config/keys.env — at minimum set ANTHROPIC_API_KEY

# 3. Run database migration
python migrate.py

# 4. Build the UI (requires Node.js 18+)
cd ui && npm install && npm run build && cd ..

# 5. Start the server
python server.py
# Open http://localhost:8000
```

The server binds to `127.0.0.1` (localhost only) by default. Set `ARIS_HOST=0.0.0.0` in `config/keys.env` only if you need LAN access — ARIS has no authentication layer.

---

## Common Commands

```bash
python main.py run                    # full pipeline (fetch + summarise)
python main.py run --domain ai        # AI regulation only
python main.py run --domain privacy   # data privacy only
python main.py fetch --days 90        # longer lookback
python main.py summarize --force      # bypass pre-filter

python reset.py                       # interactive data reset
python reset.py --documents --learning --yes   # clear docs + learning state
python migrate.py                     # safe to re-run after updates

python diagnose_legiscan.py           # diagnose LegiScan quota and session issues
python diagnose_legiscan.py MI OH NV  # test specific states only
```

---

## After Updating Files

```bash
python migrate.py          # adds new tables/columns
cd ui && npm run build     # only if UI source files changed
python server.py           # restart
```

---

## Configuration (`config/keys.env`)

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | `anthropic` / `openai` / `ollama` / `gemini` |
| `ANTHROPIC_API_KEY` | — | Required for all AI features |
| `REGULATIONS_GOV_KEY` | — | Free — federal rulemaking dockets |
| `CONGRESS_GOV_KEY` | — | Free — US bills and hearings |
| `LEGISCAN_KEY` | — | Free — all 50 US state legislatures (~30 calls/day free) |
| `COURTLISTENER_KEY` | — | Optional free token — higher rate limits for court data |
| `ACTIVE_DOMAINS` | `both` | `ai` / `privacy` / `both` |
| `LOOKBACK_DAYS` | `30` | Days back for document searches |
| `ARIS_HOST` | `127.0.0.1` | Set to `0.0.0.0` for LAN access (no auth — use caution) |
| `NOTIFY_EMAIL` | — | Recipient for email notifications |
| `SLACK_WEBHOOK_URL` | — | Slack incoming webhook URL |

---

## LegiScan Quota Management

The free LegiScan tier allows approximately 30 API calls per day. ARIS uses `getMasterList` (1 call per state), so fetching all 50 states requires 50 calls — above the free limit.

**Strategies to stay within quota:**
- Use the Run Agents regional state grid to fetch one region per day (~10–15 states)
- Increase the lookback window (e.g. 90 days) so each run captures more history per call
- Run `python diagnose_legiscan.py` to confirm quota status before a large run
- Upgrade to LegiScan paid plan ($9/month) for unrestricted calls

When quota is exhausted, ARIS logs `LEGISCAN API ERROR` in the Run Agents log window, sets a session-level quota guard to stop burning further calls, and continues processing any non-LegiScan sources normally.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

288+ tests across multiple test files. All run without live API calls.

---

## Repository Files

| File | Purpose |
|------|---------| 
| `LICENSE` | Elastic License 2.0 — non-commercial use |
| `CHANGELOG.md` | Version history |
| `CONTRIBUTING.md` | How to add state agents, run tests, submit PRs |
| `SECURITY.md` | Network exposure, key storage, vulnerability reporting |
| `diagnose_legiscan.py` | Standalone LegiScan diagnostic — run to check quota and session status |
| `pyproject.toml` | Python 3.11+ requirement, pytest config |
| `.gitignore` | Excludes keys.env, database, caches, build artifacts |

---

## Windows Setup Notes

ARIS is developed on Unix/macOS but runs on Windows. Two issues are known on Windows:

**SyntaxError: Non-UTF-8 code** — Python on Windows defaults to ASCII encoding. All ARIS Python files include `# -*- coding: utf-8 -*-` as line 1. If you receive this error, run:

```python
import pathlib
DECL = b'# -*- coding: utf-8 -*-\n'
for p in pathlib.Path('.').rglob('*.py'):
    if 'node_modules' in str(p) or '__pycache__' in str(p):
        continue
    raw = p.read_bytes()
    if b'coding: utf-8' not in raw[:50]:
        p.write_bytes(DECL + raw)
        print(f'fixed: {p}')
```

**npm run build fails with "stream did not contain valid UTF-8"** — extend the fix above to target `.js` and `.jsx` files, or save the affected file as UTF-8 in your editor.

---

## Design Principles

**Baselines are the starting point.** ARIS knows what each law requires before fetching a single new document. Every analysis is anchored to settled law.

**Signal quality over coverage.** A compliance tool that surfaces noise erodes trust faster than it builds it. The pre-filter, false-positive blocklist, and autonomous learning loop all serve this goal.

**Everything runs locally.** Database, cache, PDFs, learning state, all 32 baselines, and the horizon calendar live on your machine.

**Zero-cost features first.** Browse baselines, view the obligation register, check velocity, and see the horizon calendar without spending a single API token.

**Transparency over silence.** Pre-filter rejections are recorded as `Skipped` with the reason visible in the UI. Auto-archived documents are stamped `user="aris_auto"`. LegiScan quota errors surface in the run log rather than failing silently.

**Graceful degradation.** Failed source tracks don't block others. The seeded horizon dataset ensures the horizon view is never empty when live APIs are unavailable. International sources with unreliable feeds (e.g. Japan's METI) fall back to Google News RSS automatically.
