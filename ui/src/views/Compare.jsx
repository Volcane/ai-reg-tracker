/**
 * ARIS - Jurisdiction Comparison View
 *
 * Side-by-side structured comparison of any two regulations (baselines or documents).
 * Uses the existing /api/compare endpoint and CompareAgent.
 *
 * Layout:
 *   - Left sidebar: selector for A vs B + optional focus topic + recent comparisons
 *   - Right panel: structured results (summary, agreements, divergences, stricter-on, notes)
 */

import { useState, useEffect, useRef } from 'react'
import {
  GitCompare, ChevronDown, ChevronUp, ChevronRight, Search,
  ArrowLeftRight, RefreshCw, Star, StarOff,
  BookOpen, FileText, Sparkles, X, Clock,
  CheckCircle2, AlertTriangle, Scale,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Spinner, EmptyState, Badge } from '../components.jsx'

// ── Constants ─────────────────────────────────────────────────────────────────

const AI_COLOR      = 'var(--accent)'
const PRIVACY_COLOR = '#7c9ef7'

// All 31 baselines grouped by domain then jurisdiction
const BASELINES = [
  // AI Regulation
  { id: 'eu_ai_act',        label: 'EU AI Act',            jurisdiction: 'EU',      domain: 'ai',      priority: 'critical' },
  { id: 'eu_gdpr_ai',       label: 'EU GDPR (AI)',         jurisdiction: 'EU',      domain: 'ai',      priority: 'high'     },
  { id: 'eu_dsa_dma',       label: 'EU DSA/DMA',           jurisdiction: 'EU',      domain: 'ai',      priority: 'high'     },
  { id: 'eu_ai_liability',  label: 'EU AI Liability',      jurisdiction: 'EU',      domain: 'ai',      priority: 'high'     },
  { id: 'uk_ai_framework',  label: 'UK AI Framework',      jurisdiction: 'GB',      domain: 'ai',      priority: 'high'     },
  { id: 'us_eo_14110',      label: 'EO 14110',             jurisdiction: 'Federal', domain: 'ai',      priority: 'high'     },
  { id: 'us_nist_ai_rmf',   label: 'NIST AI RMF',          jurisdiction: 'Federal', domain: 'ai',      priority: 'high'     },
  { id: 'us_ftc_ai',        label: 'FTC AI Guidance',      jurisdiction: 'Federal', domain: 'ai',      priority: 'high'     },
  { id: 'us_sector_ai',     label: 'US Sector AI',         jurisdiction: 'Federal', domain: 'ai',      priority: 'high'     },
  { id: 'california_ai',    label: 'California AI',        jurisdiction: 'CA_STATE',domain: 'ai',      priority: 'high'     },
  { id: 'colorado_ai',      label: 'Colorado AI Act',      jurisdiction: 'CO',      domain: 'ai',      priority: 'medium'   },
  { id: 'illinois_aipa',    label: 'Illinois AIPA',        jurisdiction: 'IL',      domain: 'ai',      priority: 'medium'   },
  { id: 'nyc_ll144',        label: 'NYC Local Law 144',    jurisdiction: 'NY',      domain: 'ai',      priority: 'high'     },
  { id: 'canada_aida',      label: 'Canada AIDA',          jurisdiction: 'CA',      domain: 'ai',      priority: 'medium'   },
  { id: 'japan_ai',         label: 'Japan AI Guidelines',  jurisdiction: 'JP',      domain: 'ai',      priority: 'medium'   },
  { id: 'australia_ai',     label: 'Australia AI',         jurisdiction: 'AU',      domain: 'ai',      priority: 'medium'   },
  { id: 'brazil_ai',        label: 'Brazil AI',            jurisdiction: 'BR',      domain: 'ai',      priority: 'medium'   },
  { id: 'singapore_ai',     label: 'Singapore AI',         jurisdiction: 'SG',      domain: 'ai',      priority: 'medium'   },
  { id: 'oecd_ai_principles',label: 'OECD / G7 AI',       jurisdiction: 'INTL',    domain: 'ai',      priority: 'medium'   },
  // Data Privacy
  { id: 'eu_gdpr_full',     label: 'GDPR',                 jurisdiction: 'EU',      domain: 'privacy', priority: 'critical' },
  { id: 'uk_gdpr_dpa',      label: 'UK GDPR / DPA',       jurisdiction: 'GB',      domain: 'privacy', priority: 'high'     },
  { id: 'ccpa_cpra',        label: 'CCPA / CPRA',          jurisdiction: 'CA_STATE',domain: 'privacy', priority: 'critical' },
  { id: 'us_state_privacy', label: 'US State Privacy',     jurisdiction: 'Federal', domain: 'privacy', priority: 'high'     },
  { id: 'us_privacy_federal',label:'US Federal Privacy',  jurisdiction: 'Federal', domain: 'privacy', priority: 'high'     },
  { id: 'canada_pipeda_c27',label: 'PIPEDA / CPPA',        jurisdiction: 'CA',      domain: 'privacy', priority: 'high'     },
  { id: 'brazil_lgpd',      label: 'LGPD',                 jurisdiction: 'BR',      domain: 'privacy', priority: 'high'     },
  { id: 'japan_appi',       label: 'Japan APPI',           jurisdiction: 'JP',      domain: 'privacy', priority: 'medium'   },
  { id: 'australia_privacy',label: 'Australia Privacy',    jurisdiction: 'AU',      domain: 'privacy', priority: 'medium'   },
  { id: 'singapore_pdpa',   label: 'Singapore PDPA',       jurisdiction: 'SG',      domain: 'privacy', priority: 'medium'   },
  { id: 'eu_data_act',      label: 'EU Data Act',          jurisdiction: 'EU',      domain: 'privacy', priority: 'medium'   },
  { id: 'eu_eprivacy',      label: 'ePrivacy / Cookie Law',jurisdiction: 'EU',      domain: 'privacy', priority: 'medium'   },
]

// Common focus topics
const FOCUS_TOPICS = [
  // AI-focused
  'risk classification', 'transparency obligations', 'human oversight',
  'prohibited uses', 'conformity assessment', 'penalties and enforcement',
  'foundation models', 'high-risk AI systems',
  // Privacy-focused
  'consent requirements', 'data breach notification', 'individual rights',
  'data transfers', 'legitimate interest', 'data minimisation',
  // Cross-domain
  'automated decision-making', 'accountability', 'bias and fairness',
]

const STORAGE_KEY = 'aris_compare_history'

// ── API ───────────────────────────────────────────────────────────────────────

const compareApi = {
  run: (idA, idB, focus) =>
    fetch('/api/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_id_a:   idA,
        source_type_a: 'baseline',
        source_id_b:   idB,
        source_type_b: 'baseline',
        focus:         focus || null,
      }),
    }).then(r => r.json()),
  baselines: () => fetch('/api/baselines').then(r => r.json()),
}

// ── History helpers ───────────────────────────────────────────────────────────

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch { return [] }
}
function saveHistory(entry) {
  try {
    const h = [entry, ...loadHistory().filter(e => !(e.idA === entry.idA && e.idB === entry.idB && e.focus === entry.focus))].slice(0, 12)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(h))
  } catch {}
}

// ── Main view ─────────────────────────────────────────────────────────────────

export default function Compare() {
  const [idA,     setIdA]     = useState('')
  const [idB,     setIdB]     = useState('')
  const [focus,   setFocus]   = useState('')
  const [result,  setResult]  = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [history, setHistory] = useState(loadHistory)
  const [starred, setStarred] = useState([])

  const metaA = BASELINES.find(b => b.id === idA)
  const metaB = BASELINES.find(b => b.id === idB)
  const canRun = idA && idB && idA !== idB

  const run = async () => {
    if (!canRun) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const r = await compareApi.run(idA, idB, focus)
      if (r.error) { setError(r.error); return }
      setResult(r)
      const entry = { idA, idB, focus, title: r.title, ts: Date.now() }
      saveHistory(entry)
      setHistory(loadHistory())
    } catch (e) {
      setError(e.message || 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  const loadFromHistory = (entry) => {
    setIdA(entry.idA)
    setIdB(entry.idB)
    setFocus(entry.focus || '')
    setResult(null)
  }

  const swap = () => { setIdA(idB); setIdB(idA); setResult(null) }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── Left sidebar ── */}
      <aside style={{
        width: 260, flexShrink: 0,
        borderRight: '1px solid var(--border)',
        overflow: 'auto', padding: '18px 14px',
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <div>
          <div style={{ fontWeight: 500, fontSize: 14, marginBottom: 2 }}>Compare Regulations</div>
          <div style={{ fontSize: 11, color: 'var(--text-3)' }}>
            Side-by-side AI analysis of two frameworks
          </div>
        </div>

        {/* Regulation A */}
        <RegSelector
          label="Regulation A"
          value={idA}
          onChange={v => { setIdA(v); setResult(null) }}
          exclude={idB}
          color={AI_COLOR}
          slot="A"
        />

        {/* Swap button */}
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <button
            className="btn-secondary btn-sm"
            onClick={swap}
            disabled={!idA && !idB}
            title="Swap A and B"
            style={{ gap: 6 }}
          >
            <ArrowLeftRight size={12} /> Swap
          </button>
        </div>

        {/* Regulation B */}
        <RegSelector
          label="Regulation B"
          value={idB}
          onChange={v => { setIdB(v); setResult(null) }}
          exclude={idA}
          color={PRIVACY_COLOR}
          slot="B"
        />

        {/* Focus topic */}
        <div>
          <label style={{ fontSize: 11, color: 'var(--text-3)', display: 'block', marginBottom: 6, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Focus (optional)
          </label>
          <input
            placeholder="e.g. consent, penalties…"
            value={focus}
            onChange={e => setFocus(e.target.value)}
            style={{ marginBottom: 8, fontSize: 12 }}
          />
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {FOCUS_TOPICS.filter(t =>
              // Show relevant topics based on selection domain
              !idA || !idB || true  // show all when nothing selected
            ).slice(0, 8).map(t => (
              <button
                key={t}
                onClick={() => setFocus(focus === t ? '' : t)}
                style={{
                  fontSize: 10, padding: '2px 7px', borderRadius: 10, cursor: 'pointer',
                  background: focus === t ? 'var(--accent-dim)' : 'var(--bg-3)',
                  border: `1px solid ${focus === t ? 'var(--accent)' : 'var(--border)'}`,
                  color: focus === t ? 'var(--accent)' : 'var(--text-3)',
                  transition: 'all 0.1s',
                }}
              >{t}</button>
            ))}
          </div>
        </div>

        {/* Run button */}
        <button
          className="btn-primary"
          style={{ width: '100%', justifyContent: 'center', fontSize: 13 }}
          onClick={run}
          disabled={!canRun || loading}
        >
          {loading
            ? <><Spinner size={13} /> Analysing…</>
            : <><GitCompare size={13} /> Compare</>
          }
        </button>

        {!canRun && idA && idB && idA === idB && (
          <div style={{ fontSize: 11, color: 'var(--red)', textAlign: 'center' }}>
            Select two different regulations
          </div>
        )}

        {/* History */}
        {history.length > 0 && (
          <div>
            <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
              Recent
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {history.slice(0, 6).map((h, i) => {
                const mA = BASELINES.find(b => b.id === h.idA)
                const mB = BASELINES.find(b => b.id === h.idB)
                return (
                  <button
                    key={i}
                    onClick={() => loadFromHistory(h)}
                    style={{
                      textAlign: 'left', padding: '7px 9px',
                      background: 'var(--bg-3)', border: '1px solid var(--border)',
                      borderRadius: 'var(--radius)', cursor: 'pointer',
                      transition: 'border-color 0.1s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-hi)'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                  >
                    <div style={{ fontSize: 11, color: 'var(--text-2)', marginBottom: 2 }} className="truncate">
                      {mA?.label || h.idA} <span style={{ color: 'var(--text-3)' }}>vs</span> {mB?.label || h.idB}
                    </div>
                    {h.focus && (
                      <div style={{ fontSize: 10, color: 'var(--text-3)', fontStyle: 'italic' }} className="truncate">
                        focus: {h.focus}
                      </div>
                    )}
                    <div style={{ fontSize: 9, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                      {new Date(h.ts).toLocaleDateString()}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </aside>

      {/* ── Right panel ── */}
      <main style={{ flex: 1, overflow: 'auto', minWidth: 0 }}>
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 16 }}>
            <Spinner size={28} />
            <div style={{ fontSize: 13, color: 'var(--text-3)' }}>
              Claude is reading both regulations and building the comparison…
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
              {metaA?.label} vs {metaB?.label}
              {focus && ` · focus: ${focus}`}
            </div>
          </div>
        ) : error ? (
          <div style={{ padding: '32px 36px' }}>
            <div style={{ padding: '14px 16px', background: 'rgba(224,82,82,0.08)', border: '1px solid rgba(224,82,82,0.3)', borderRadius: 'var(--radius)', color: 'var(--red)', fontSize: 13, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <div style={{ fontWeight: 500, marginBottom: 4 }}>Comparison failed</div>
                <div>{error}</div>
                {error.includes('not configured') && (
                  <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-3)' }}>
                    Jurisdiction comparison requires an Anthropic API key. Configure it in Settings.
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : result ? (
          <CompareResult
            result={result}
            metaA={metaA}
            metaB={metaB}
            onRerun={run}
            loading={loading}
          />
        ) : (
          <ComparePlaceholder
            history={history}
            onLoad={loadFromHistory}
            onSelect={(a, b, f) => { setIdA(a); setIdB(b); if (f) setFocus(f) }}
          />
        )}
      </main>
    </div>
  )
}

// ── Regulation selector ───────────────────────────────────────────────────────

function RegSelector({ label, value, onChange, exclude, color, slot }) {
  const [open,   setOpen]   = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const selected = BASELINES.find(b => b.id === value)

  const groups = [
    { label: 'AI Regulation', domain: 'ai',      color: AI_COLOR      },
    { label: 'Data Privacy',  domain: 'privacy',  color: PRIVACY_COLOR },
  ]

  const filtered = (domain) => BASELINES.filter(b =>
    b.domain === domain &&
    b.id !== exclude &&
    (!search || b.label.toLowerCase().includes(search.toLowerCase()) ||
                b.jurisdiction.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 5 }}>
        {label}
      </div>

      <button
        onClick={() => setOpen(!open)}
        style={{
          width: '100%', textAlign: 'left', padding: '8px 10px',
          background: selected ? 'var(--bg-4)' : 'var(--bg-3)',
          border: `1px solid ${selected ? color + '55' : 'var(--border)'}`,
          borderRadius: 'var(--radius)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 7,
          transition: 'all 0.1s',
        }}
      >
        {selected ? (
          <>
            <span style={{
              width: 16, height: 16, borderRadius: 4, display: 'flex', alignItems: 'center',
              justifyContent: 'center', background: color + '22', flexShrink: 0,
              fontSize: 9, fontWeight: 700, color, fontFamily: 'var(--font-mono)',
            }}>{slot}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)' }} className="truncate">{selected.label}</div>
              <div style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>{selected.jurisdiction}</div>
            </div>
          </>
        ) : (
          <>
            <span style={{
              width: 16, height: 16, borderRadius: 4, display: 'flex', alignItems: 'center',
              justifyContent: 'center', background: 'var(--bg-4)', flexShrink: 0,
              fontSize: 9, fontWeight: 700, color: 'var(--text-3)', fontFamily: 'var(--font-mono)',
            }}>{slot}</span>
            <span style={{ fontSize: 12, color: 'var(--text-3)', flex: 1 }}>Select regulation…</span>
          </>
        )}
        <ChevronDown size={12} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
      </button>

      {open && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
          background: 'var(--bg-2)', border: '1px solid var(--border-hi)',
          borderRadius: 'var(--radius-lg)', boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          marginTop: 4, overflow: 'hidden',
        }}>
          <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ position: 'relative' }}>
              <Search size={11} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)' }} />
              <input
                autoFocus
                placeholder="Search…"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ paddingLeft: 24, fontSize: 12, width: '100%', boxSizing: 'border-box' }}
              />
            </div>
          </div>
          <div style={{ maxHeight: 280, overflow: 'auto' }}>
            {groups.map(g => {
              const items = filtered(g.domain)
              if (!items.length) return null
              return (
                <div key={g.domain}>
                  <div style={{ padding: '6px 10px 3px', fontSize: 9, fontFamily: 'var(--font-mono)', color: g.color, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    {g.label}
                  </div>
                  {items.map(b => (
                    <div
                      key={b.id}
                      onClick={() => { onChange(b.id); setOpen(false); setSearch('') }}
                      style={{
                        padding: '7px 10px', cursor: 'pointer',
                        background: value === b.id ? 'var(--bg-4)' : 'transparent',
                        display: 'flex', alignItems: 'center', gap: 8,
                        transition: 'background 0.08s',
                      }}
                      onMouseEnter={e => { if (value !== b.id) e.currentTarget.style.background = 'var(--bg-3)' }}
                      onMouseLeave={e => { if (value !== b.id) e.currentTarget.style.background = 'transparent' }}
                    >
                      <span style={{
                        fontSize: 9, fontFamily: 'var(--font-mono)', padding: '1px 5px',
                        borderRadius: 3, background: 'var(--bg-4)', color: 'var(--text-3)',
                      }}>{b.jurisdiction}</span>
                      <span style={{ flex: 1, fontSize: 12, color: value === b.id ? g.color : 'var(--text-2)' }}>
                        {b.label}
                      </span>
                      {b.priority === 'critical' && (
                        <span style={{ fontSize: 9, color: 'var(--red)', fontFamily: 'var(--font-mono)' }}>★</span>
                      )}
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Comparison result ─────────────────────────────────────────────────────────

function CompareResult({ result, metaA, metaB, onRerun, loading }) {
  const [expandedDiv, setExpandedDiv] = useState({})
  const toggle = (key) => setExpandedDiv(p => ({ ...p, [key]: !p[key] }))

  const srcA = result.source_a || {}
  const srcB = result.source_b || {}
  const colorA = metaA?.domain === 'privacy' ? PRIVACY_COLOR : AI_COLOR
  const colorB = metaB?.domain === 'privacy' ? PRIVACY_COLOR : AI_COLOR

  return (
    <div style={{ padding: '24px 28px', maxWidth: 900, width: '100%', boxSizing: 'border-box' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20, gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          {/* A vs B labels */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
            <RegChip label={srcA.title || metaA?.label} color={colorA} slot="A" meta={metaA} />
            <span style={{ fontSize: 13, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>vs</span>
            <RegChip label={srcB.title || metaB?.label} color={colorB} slot="B" meta={metaB} />
            {result.focus && (
              <span style={{
                fontSize: 11, padding: '2px 8px', borderRadius: 10,
                background: 'var(--accent-glow)', color: 'var(--accent)',
                border: '1px solid var(--accent-dim)',
              }}>
                focus: {result.focus}
              </span>
            )}
          </div>

          {/* Summary */}
          {result.summary && (
            <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.7, margin: 0 }}>
              {result.summary}
            </p>
          )}
        </div>

        <button className="btn-ghost btn-sm" onClick={onRerun} disabled={loading} style={{ flexShrink: 0 }}>
          <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
        </button>
      </div>

      {/* Stricter-on quick view */}
      {((result.a_stricter_on?.length > 0) || (result.b_stricter_on?.length > 0)) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
          <StricterBox
            label={srcA.title || metaA?.label}
            slot="A"
            color={colorA}
            items={result.a_stricter_on || []}
          />
          <StricterBox
            label={srcB.title || metaB?.label}
            slot="B"
            color={colorB}
            items={result.b_stricter_on || []}
          />
        </div>
      )}

      {/* Divergences - the main section */}
      {result.divergences?.length > 0 && (
        <Section title="Divergences" count={result.divergences.length} icon={Scale} defaultOpen>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {result.divergences.map((div, i) => (
              <DivergenceCard
                key={i}
                div={div}
                labelA={srcA.title || metaA?.label}
                labelB={srcB.title || metaB?.label}
                colorA={colorA}
                colorB={colorB}
                expanded={!!expandedDiv[i]}
                onToggle={() => toggle(i)}
              />
            ))}
          </div>
        </Section>
      )}

      {/* Agreements */}
      {result.agreements?.length > 0 && (
        <Section title="Agreements" count={result.agreements.length} icon={CheckCircle2}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
            {result.agreements.map((ag, i) => (
              <div key={i} style={{
                padding: '9px 13px', background: 'rgba(82,168,120,0.07)',
                border: '1px solid rgba(82,168,120,0.2)', borderRadius: 'var(--radius)',
              }}>
                <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--green)', marginBottom: 3 }}>
                  {ag.area}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.55 }}>
                  {ag.description}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Practical notes */}
      {result.practical_notes?.length > 0 && (
        <Section title="Practical Notes" icon={BookOpen} subtitle="For organisations subject to both">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {result.practical_notes.map((note, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6 }}>
                <span style={{ color: 'var(--accent)', flexShrink: 0, marginTop: 2, fontSize: 10 }}> - </span>
                {note}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Footer: model + citations */}
      <div style={{ marginTop: 20, paddingTop: 14, borderTop: '1px solid var(--border)', display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-3)', flexWrap: 'wrap', alignItems: 'center' }}>
        {result.model_used && (
          <span style={{ fontFamily: 'var(--font-mono)' }}>
            <Sparkles size={10} style={{ marginRight: 4, verticalAlign: 'middle' }} />
            {result.model_used}
          </span>
        )}
        {result.citations?.length > 0 && (
          <span>
            Citations: {result.citations.map(c => (
              <span key={c.source_id} style={{ marginRight: 6, background: 'var(--bg-4)', padding: '1px 5px', borderRadius: 3, fontFamily: 'var(--font-mono)' }}>
                {c.source_id}
              </span>
            ))}
          </span>
        )}
      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function RegChip({ label, color, slot, meta }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{
        width: 18, height: 18, borderRadius: 4, display: 'flex', alignItems: 'center',
        justifyContent: 'center', background: color + '22', flexShrink: 0,
        fontSize: 9, fontWeight: 700, color, fontFamily: 'var(--font-mono)',
      }}>{slot}</span>
      <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)' }}>{label}</span>
      {meta && (
        <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-3)', background: 'var(--bg-4)', padding: '1px 5px', borderRadius: 3 }}>
          {meta.jurisdiction}
        </span>
      )}
    </div>
  )
}

function StricterBox({ label, slot, color, items }) {
  if (!items.length) return (
    <div style={{ padding: '10px 13px', background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', opacity: 0.5 }}>
      <div style={{ fontSize: 11, color: 'var(--text-3)', fontStyle: 'italic' }}>No areas where {label} is strictly more demanding</div>
    </div>
  )
  return (
    <div style={{ padding: '10px 13px', background: color + '0a', border: `1px solid ${color}30`, borderRadius: 'var(--radius)' }}>
      <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 7, display: 'flex', alignItems: 'center', gap: 5 }}>
        <span style={{ width: 14, height: 14, borderRadius: 3, background: color + '22', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 700 }}>{slot}</span>
        {label} is stricter on:
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
        {items.map((item, i) => (
          <span key={i} style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 4,
            background: color + '15', color,
            border: `1px solid ${color}30`,
          }}>{item}</span>
        ))}
      </div>
    </div>
  )
}

function Section({ title, count, icon: Icon, subtitle, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ marginBottom: 16 }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left',
          background: 'transparent', border: 'none', cursor: 'pointer',
          padding: '8px 0', borderTop: '1px solid var(--border)', marginBottom: open ? 12 : 0,
        }}
      >
        {Icon && <Icon size={13} style={{ color: 'var(--text-3)', flexShrink: 0 }} />}
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)' }}>{title}</span>
        {count !== undefined && (
          <span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', background: 'var(--bg-4)', padding: '0 5px', borderRadius: 3 }}>
            {count}
          </span>
        )}
        {subtitle && <span style={{ fontSize: 11, color: 'var(--text-3)', marginLeft: 4 }}>{subtitle}</span>}
        <span style={{ marginLeft: 'auto', color: 'var(--text-3)' }}>
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </span>
      </button>
      {open && children}
    </div>
  )
}

function DivergenceCard({ div, labelA, labelB, colorA, colorB, expanded, onToggle }) {
  return (
    <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '10px 14px', cursor: 'pointer' }} onClick={onToggle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)', flex: 1 }}>
            {div.area}
          </span>
          {expanded ? <ChevronUp size={13} style={{ color: 'var(--text-3)', flexShrink: 0 }} /> : <ChevronDown size={13} style={{ color: 'var(--text-3)', flexShrink: 0 }} />}
        </div>
        {!expanded && div.significance && (
          <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: 3, lineHeight: 1.4 }} className="truncate">
            {div.significance}
          </div>
        )}
      </div>

      {/* Expanded: side-by-side approaches */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0 }}>
            {[
              { label: labelA, approach: div.a_approach, color: colorA, slot: 'A' },
              { label: labelB, approach: div.b_approach, color: colorB, slot: 'B' },
            ].map((side, i) => (
              <div key={i} style={{
                padding: '12px 14px',
                borderRight: i === 0 ? '1px solid var(--border)' : 'none',
                background: i === 0 ? 'var(--bg-3)' : 'var(--bg-2)',
              }}>
                <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: side.color, marginBottom: 7, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 14, height: 14, borderRadius: 3, background: side.color + '22', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 8, fontWeight: 700 }}>{side.slot}</span>
                  {side.label}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.6 }}>
                  {side.approach}
                </div>
              </div>
            ))}
          </div>
          {div.significance && (
            <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border)', background: 'var(--bg-3)', fontSize: 12, color: 'var(--text-3)', lineHeight: 1.5, fontStyle: 'italic' }}>
              <span style={{ color: 'var(--accent)', marginRight: 5, fontStyle: 'normal', fontSize: 10 }}>Why it matters</span>
              {div.significance}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Placeholder ───────────────────────────────────────────────────────────────

const SUGGESTED_PAIRS = [
  { idA: 'eu_ai_act',    idB: 'us_nist_ai_rmf',  focus: 'risk classification',  label: 'EU AI Act vs NIST RMF - risk tiers' },
  { idA: 'eu_gdpr_full', idB: 'ccpa_cpra',        focus: 'consent requirements', label: 'GDPR vs CCPA - consent' },
  { idA: 'eu_ai_act',    idB: 'eu_gdpr_full',     focus: 'automated decision-making', label: 'EU AI Act vs GDPR - automated decisions' },
  { idA: 'eu_gdpr_full', idB: 'uk_gdpr_dpa',      focus: 'data transfers',       label: 'GDPR vs UK GDPR - transfers post-Brexit' },
  { idA: 'eu_ai_act',    idB: 'colorado_ai',      focus: 'risk classification',  label: 'EU AI Act vs Colorado - risk approach' },
  { idA: 'ccpa_cpra',    idB: 'us_state_privacy', focus: 'individual rights',    label: 'CCPA vs US State Privacy - rights scope' },
]

function ComparePlaceholder({ history, onLoad, onSelect }) {
  return (
    <div style={{ padding: '36px 36px', maxWidth: 680 }}>
      <GitCompare size={32} style={{ color: 'var(--accent)', marginBottom: 16 }} />
      <h2 style={{ fontWeight: 300, fontSize: '1.4rem', marginBottom: 10 }}>Jurisdiction Comparison</h2>
      <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.75, marginBottom: 28 }}>
        Select any two regulations on the left and Claude will produce a structured
        side-by-side analysis - where they diverge, where they agree, which is stricter,
        and what it means for organisations subject to both.
      </p>

      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 12 }}>
        Suggested comparisons
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {SUGGESTED_PAIRS.map((p, i) => {
          const mA = BASELINES.find(b => b.id === p.idA)
          const mB = BASELINES.find(b => b.id === p.idB)
          return (
            <button
              key={i}
              onClick={() => onSelect(p.idA, p.idB, p.focus)}
              style={{
                textAlign: 'left', padding: '10px 14px',
                background: 'var(--bg-2)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 10,
                transition: 'all 0.1s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-hi)'; e.currentTarget.style.background = 'var(--bg-3)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--bg-2)' }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, color: 'var(--text)', marginBottom: 3 }}>{p.label}</div>
                <div style={{ display: 'flex', gap: 5 }}>
                  <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', background: 'var(--bg-4)', color: 'var(--text-3)', padding: '1px 4px', borderRadius: 3 }}>{mA?.jurisdiction}</span>
                  <span style={{ fontSize: 9, color: 'var(--text-3)' }}>vs</span>
                  <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', background: 'var(--bg-4)', color: 'var(--text-3)', padding: '1px 4px', borderRadius: 3 }}>{mB?.jurisdiction}</span>
                  {p.focus && <span style={{ fontSize: 9, color: 'var(--accent)', background: 'var(--accent-glow)', padding: '1px 5px', borderRadius: 3 }}>focus: {p.focus}</span>}
                </div>
              </div>
              <ChevronRight size={13} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
            </button>
          )
        })}
      </div>
    </div>
  )
}
