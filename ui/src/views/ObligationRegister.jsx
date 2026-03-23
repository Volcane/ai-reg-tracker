/**
 * ARIS - Obligation Register
 *
 * Top-level view for the consolidated obligation register.
 * Shows every distinct compliance obligation across all loaded baselines
 * for the selected jurisdictions - deduplicated, categorised, and sortable.
 *
 * Two modes:
 *   Fast  - structural consolidation from baselines only, instant, no API call
 *   Full  - Claude-verified semantic deduplication, one API call, cached 24h
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  ListChecks, RefreshCw, Download, ChevronDown, ChevronUp,
  Globe, AlertTriangle, Search, Filter, Sparkles, Clock,
  CheckCircle2, Shield, FileText, Eye, Settings, Database,
  Scale, X,
} from 'lucide-react'
import { Spinner, EmptyState, Badge, DomainFilter } from '../components.jsx'

// ── API ───────────────────────────────────────────────────────────────────────

const regApi = {
  get:        (jurs, mode='fast', force=false) =>
    fetch(`/api/register?jurisdictions=${encodeURIComponent(jurs.join(','))}&mode=${mode}&force=${force}`)
      .then(r => r.json()),
  refresh:    (jurs, mode='full') =>
    fetch('/api/register/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jurisdictions: jurs, mode }),
    }).then(r => r.json()),
  categories: () => fetch('/api/register/categories').then(r => r.json()),
  baselines:  () => fetch('/api/baselines').then(r => r.json()),
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORY_META = {
  'Prohibition':   { icon: Shield,       color: 'var(--red)',    bg: 'rgba(224,82,82,0.10)'   },
  'Assessment':    { icon: ListChecks,     color: 'var(--orange)', bg: 'rgba(224,131,74,0.10)'  },
  'Oversight':     { icon: Eye,           color: 'var(--accent)', bg: 'var(--accent-glow)'     },
  'Transparency':  { icon: Eye,           color: 'var(--yellow)', bg: 'rgba(212,168,67,0.10)'  },
  'Governance':    { icon: Scale,         color: 'var(--text-2)', bg: 'var(--bg-3)'            },
  'Documentation': { icon: FileText,      color: 'var(--text-2)', bg: 'var(--bg-3)'            },
  'Reporting':     { icon: FileText,      color: 'var(--text-2)', bg: 'var(--bg-3)'            },
  'Technical':     { icon: Settings,       color: 'var(--accent)', bg: 'var(--accent-glow)'     },
  'Rights':        { icon: CheckCircle2,  color: 'var(--green)',  bg: 'rgba(82,168,120,0.10)'  },
  'Training Data': { icon: Database,      color: 'var(--text-2)', bg: 'var(--bg-3)'            },
}

const UNIVERSALITY_META = {
  'Universal':           { color: 'var(--red)',    label: 'Universal'    },
  'Majority':            { color: 'var(--orange)', label: 'Majority'     },
  'Single jurisdiction': { color: 'var(--text-3)', label: 'Single'       },
}

// Preset jurisdiction bundles
const PRESETS = [
  { label: 'All',        jurs: ['Federal','EU','GB','CA','PA','IL','VA','CO','JP','AU','SG','BR'] },
  { label: 'US Core',    jurs: ['Federal','PA','IL','VA','CO'] },
  { label: 'EU / UK',    jurs: ['EU','GB'] },
  { label: 'Privacy',    jurs: ['EU','GB','CA','JP','AU','SG','BR','Federal'] },
  { label: 'AI Reg',     jurs: ['EU','Federal','GB','IL','VA','CO'] },
]

const ALL_JURS = ['Federal','EU','GB','CA','PA','IL','VA','CO','JP','AU','SG','BR']

const AI_COLOR      = 'var(--accent)'
const PRIVACY_COLOR = '#7c9ef7'

// ── Main view ─────────────────────────────────────────────────────────────────

export default function ObligationRegister() {
  // Jurisdiction selection - persisted
  const [selectedJurs, setSelectedJurs] = useState(() => {
    try {
      const s = localStorage.getItem('aris_register_jurs')
      return s ? JSON.parse(s) : ['EU','Federal','GB']
    } catch { return ['EU','Federal','GB'] }
  })

  // Domain filter
  const [domain, setDomain] = useState(() => {
    try { return localStorage.getItem('aris_domain_register') ?? null } catch { return null }
  })

  // Register data
  const [register,   setRegister]   = useState([])
  const [loading,    setLoading]    = useState(false)
  const [upgrading,  setUpgrading]  = useState(false)
  const [mode,       setMode]       = useState('fast')  // fast | full
  const [loadedFor,  setLoadedFor]  = useState(null)    // stringified jurs that are loaded
  const [error,      setError]      = useState(null)

  // Filters
  const [search,       setSearch]       = useState('')
  const [catFilter,    setCatFilter]    = useState('')
  const [univFilter,   setUnivFilter]   = useState('')
  const [sortBy,       setSortBy]       = useState('category')  // category | deadline | universality | sources
  const [expanded,     setExpanded]     = useState({})

  // Track available baselines for showing domain counts
  const [baselines, setBaselines] = useState([])

  // Load baselines metadata once
  useEffect(() => {
    regApi.baselines().then(b => setBaselines(Array.isArray(b) ? b : [])).catch(() => {})
  }, [])

  const saveJurs = useCallback((jurs) => {
    setSelectedJurs(jurs)
    try { localStorage.setItem('aris_register_jurs', JSON.stringify(jurs)) } catch {}
  }, [])

  const handleDomainChange = useCallback((d) => {
    setDomain(d)
    try { localStorage.setItem('aris_domain_register', d ?? '') } catch {}
  }, [])

  // Load register whenever jurisdiction selection changes
  const loadRegister = useCallback(async (jurs = selectedJurs, m = mode, force = false) => {
    if (!jurs.length) return
    setLoading(true)
    setError(null)
    try {
      const res = await regApi.get(jurs, m, force)
      setRegister(res.items || [])
      setMode(m)
      setLoadedFor(JSON.stringify(jurs))
    } catch (e) {
      setError(e.message || 'Failed to load register')
    } finally {
      setLoading(false)
    }
  }, [selectedJurs, mode])

  const upgradeToFull = async () => {
    setUpgrading(true)
    setError(null)
    try {
      const res = await regApi.refresh(selectedJurs, 'full')
      setRegister(res.items || [])
      setMode('full')
      setLoadedFor(JSON.stringify(selectedJurs))
    } catch (e) {
      setError(e.message || 'Upgrade failed')
    } finally {
      setUpgrading(false)
    }
  }

  // Toggle a jurisdiction
  const toggleJur = (j) => {
    const next = selectedJurs.includes(j)
      ? selectedJurs.filter(x => x !== j)
      : [...selectedJurs, j]
    saveJurs(next)
  }

  const applyPreset = (preset) => {
    saveJurs(preset.jurs)
    setLoadedFor(null)  // force reload
  }

  // Privacy-relevant jurisdiction heuristic for domain filter
  const PRIVACY_JURS = new Set(['EU','GB','BR','SG','JP','AU','CA'])

  // Build filtered + sorted list
  const filtered = register.filter(obl => {
    if (catFilter && obl.category !== catFilter) return false
    if (univFilter && obl.universality !== univFilter) return false
    if (domain) {
      const oblJurs = new Set(obl.jurisdictions || [])
      const hasPrivacy = [...oblJurs].some(j => PRIVACY_JURS.has(j))
      const hasAI      = [...oblJurs].some(j => !PRIVACY_JURS.has(j))
      if (domain === 'privacy' && !hasPrivacy) return false
      if (domain === 'ai'      && !hasAI)      return false
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      return (obl.title       || '').toLowerCase().includes(q)
          || (obl.description || '').toLowerCase().includes(q)
          || (obl.category    || '').toLowerCase().includes(q)
          || (obl.jurisdictions || []).some(j => j.toLowerCase().includes(q))
    }
    return true
  }).sort((a, b) => {
    if (sortBy === 'deadline') {
      const da = a.earliest_deadline || 'z'
      const db = b.earliest_deadline || 'z'
      return da < db ? -1 : da > db ? 1 : 0
    }
    if (sortBy === 'universality') {
      const order = { 'Universal': 0, 'Majority': 1, 'Single jurisdiction': 2 }
      return (order[a.universality] ?? 3) - (order[b.universality] ?? 3)
    }
    if (sortBy === 'sources') {
      return (b.source_count || 0) - (a.source_count || 0)
    }
    // category - Prohibition first
    if (a.category === 'Prohibition' && b.category !== 'Prohibition') return -1
    if (b.category === 'Prohibition' && a.category !== 'Prohibition') return 1
    return (a.category || '').localeCompare(b.category || '') ||
           (a.title    || '').localeCompare(b.title    || '')
  })

  const categories    = [...new Set(register.map(r => r.category))].sort()
  const jursAreLoaded = loadedFor === JSON.stringify(selectedJurs)

  // Export filtered list as JSON
  const exportJson = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href     = url
    a.download = `obligation_register_${selectedJurs.join('-')}_${new Date().toISOString().slice(0,10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── Left panel - jurisdiction selector ── */}
      <aside style={{
        width: 220, flexShrink: 0,
        borderRight: '1px solid var(--border)',
        overflow: 'auto', padding: '20px 14px',
        display: 'flex', flexDirection: 'column', gap: 0,
      }}>
        <div style={{ fontWeight: 500, fontSize: 14, marginBottom: 2 }}>Obligation Register</div>
        <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 16 }}>
          Select jurisdictions to consolidate
        </div>

        {/* Presets */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
            Presets
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {PRESETS.map(p => (
              <button key={p.label}
                className="btn-ghost btn-sm"
                style={{
                  justifyContent: 'flex-start', fontSize: 12,
                  background: JSON.stringify(selectedJurs.slice().sort()) === JSON.stringify(p.jurs.slice().sort())
                    ? 'var(--bg-4)' : 'transparent',
                }}
                onClick={() => applyPreset(p)}>
                <Globe size={11} style={{ flexShrink: 0 }} />
                {p.label}
                <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                  {p.jurs.length}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Individual jurisdictions */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-3)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
            Jurisdictions
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {ALL_JURS.map(j => {
              const active = selectedJurs.includes(j)
              const isPrivacy = PRIVACY_JURS.has(j)
              return (
                <button key={j}
                  onClick={() => toggleJur(j)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 7,
                    padding: '5px 8px', borderRadius: 'var(--radius)',
                    background: active ? 'var(--bg-4)' : 'transparent',
                    border: `1px solid ${active ? 'var(--border-hi)' : 'transparent'}`,
                    cursor: 'pointer', fontSize: 12,
                    color: active ? 'var(--text)' : 'var(--text-3)',
                    transition: 'all 0.1s', textAlign: 'left',
                  }}
                  onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--bg-3)' }}
                  onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
                >
                  <span style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 11 }}>{j}</span>
                  {active && (
                    <span style={{
                      fontSize: 9, padding: '1px 4px', borderRadius: 3,
                      background: isPrivacy ? '#7c9ef720' : 'var(--accent-glow)',
                      color: isPrivacy ? PRIVACY_COLOR : AI_COLOR,
                    }}>
                      {isPrivacy ? 'PV' : 'AI'}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
          {selectedJurs.length > 0 && (
            <button className="btn-ghost btn-sm" style={{ marginTop: 6, fontSize: 11, width: '100%' }}
              onClick={() => saveJurs([])}>
              <X size={10} /> Clear all
            </button>
          )}
        </div>

        {/* Load button */}
        <button
          className="btn-primary"
          style={{ width: '100%', justifyContent: 'center', fontSize: 13 }}
          onClick={() => loadRegister(selectedJurs, 'fast')}
          disabled={loading || !selectedJurs.length}
        >
          {loading ? <><Spinner size={13} /> Loading…</> : <><ListChecks size={13} /> Load Register</>}
        </button>

        {/* Mode indicator */}
        {loadedFor && (
          <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-3)', lineHeight: 1.5 }}>
            {mode === 'fast'
              ? '⚡ Structural mode - instant from baselines'
              : '✓ Claude-verified semantic deduplication'}
            {mode === 'fast' && (
              <button
                onClick={upgradeToFull}
                disabled={upgrading}
                style={{
                  display: 'block', marginTop: 8, width: '100%',
                  padding: '5px 8px', background: 'var(--bg-3)',
                  border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                  fontSize: 11, color: 'var(--text-2)', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 5,
                }}
              >
                <Sparkles size={11} style={{ color: 'var(--accent)' }} />
                {upgrading ? 'Verifying…' : 'Upgrade to Full (Claude)'}
              </button>
            )}
          </div>
        )}
      </aside>

      {/* ── Right panel - register ── */}
      <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', minWidth: 0 }}>

        {!loadedFor && !loading ? (
          <RegisterPlaceholder onLoad={() => loadRegister()} hasJurs={selectedJurs.length > 0} />
        ) : (
          <div style={{ padding: '20px 28px', maxWidth: 1000, width: '100%', boxSizing: 'border-box' }}>

            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16, gap: 12, flexWrap: 'wrap' }}>
              <div>
                <h2 style={{ fontWeight: 300, fontSize: '1.3rem', marginBottom: 3 }}>
                  Consolidated Obligation Register
                </h2>
                <div style={{ fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                  {loading ? 'Loading…' : `${filtered.length} of ${register.length} obligations · ${selectedJurs.join(', ')}`}
                  {mode === 'full' && <span style={{ color: 'var(--green)', marginLeft: 8 }}> -  Claude-verified</span>}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <DomainFilter domain={domain} onChange={handleDomainChange} />
                <button className="btn-secondary btn-sm" onClick={exportJson} disabled={!filtered.length}>
                  <Download size={12} /> Export JSON
                </button>
                <button className="btn-ghost btn-sm" onClick={() => loadRegister(selectedJurs, mode, true)} disabled={loading}>
                  <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
                </button>
              </div>
            </div>

            {error && (
              <div style={{ marginBottom: 16, padding: '10px 14px', background: 'rgba(224,82,82,0.08)', border: '1px solid rgba(224,82,82,0.3)', borderRadius: 'var(--radius)', fontSize: 13, color: 'var(--red)', display: 'flex', gap: 8, alignItems: 'center' }}>
                <AlertTriangle size={14} style={{ flexShrink: 0 }} /> {error}
              </div>
            )}

            {/* Summary stats */}
            {!loading && register.length > 0 && (
              <RegisterStats register={register} filtered={filtered} />
            )}

            {/* Filters */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{ position: 'relative', flex: '1 1 180px', minWidth: 140 }}>
                <Search size={12} style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)', pointerEvents: 'none' }} />
                <input
                  placeholder="Search obligations…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  style={{ paddingLeft: 28, width: '100%', boxSizing: 'border-box', fontSize: 12 }}
                />
              </div>

              <select value={catFilter} onChange={e => setCatFilter(e.target.value)} style={{ fontSize: 12 }}>
                <option value="">All categories</option>
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select>

              <select value={univFilter} onChange={e => setUnivFilter(e.target.value)} style={{ fontSize: 12 }}>
                <option value="">All scope</option>
                <option value="Universal">Universal</option>
                <option value="Majority">Majority</option>
                <option value="Single jurisdiction">Single jurisdiction</option>
              </select>

              <div style={{ display: 'flex', gap: 4, marginLeft: 'auto', alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: 'var(--text-3)' }}>Sort:</span>
                {[
                  { id: 'category',    label: 'Category'  },
                  { id: 'sources',     label: 'Sources'   },
                  { id: 'deadline',    label: 'Deadline'  },
                  { id: 'universality',label: 'Scope'     },
                ].map(s => (
                  <button key={s.id}
                    className={sortBy === s.id ? 'btn-primary btn-sm' : 'btn-ghost btn-sm'}
                    style={{ fontSize: 11 }}
                    onClick={() => setSortBy(s.id)}>
                    {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* List */}
            {loading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner size={24} /></div>
            ) : filtered.length === 0 ? (
              <EmptyState
                icon={ListChecks}
                title={search ? `No obligations matching "${search}"` : 'No obligations found'}
                message={search
                  ? 'Try a different search term or clear the filters.'
                  : 'Select jurisdictions in the left panel and click Load Register.'
                }
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {filtered.map((obl, i) => (
                  <ObligationCard
                    key={i}
                    obl={obl}
                    expanded={!!expanded[i]}
                    onToggle={() => setExpanded(p => ({ ...p, [i]: !p[i] }))}
                    domain={domain}
                  />
                ))}
              </div>
            )}

            {/* Footer note */}
            {!loading && register.length > 0 && (
              <div style={{ marginTop: 20, padding: '10px 14px', background: 'var(--bg-3)', borderRadius: 'var(--radius)', fontSize: 11, color: 'var(--text-3)', lineHeight: 1.6 }}>
                {mode === 'fast'
                  ? '⚡ Structural consolidation: obligations grouped by category, merged by title similarity. No API call. Click "Upgrade to Full" for Claude-verified semantic deduplication.'
                  : '✓ Claude-verified: obligations have been semantically deduplicated and categorised. Results cached 24 hours.'}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

// ── Summary stats bar ─────────────────────────────────────────────────────────

function RegisterStats({ register, filtered }) {
  const byCategory = register.reduce((acc, o) => {
    acc[o.category] = (acc[o.category] || 0) + 1
    return acc
  }, {})
  const universal  = register.filter(o => o.universality === 'Universal').length
  const withDeadline = register.filter(o => o.earliest_deadline).length
  const prohibitions = byCategory['Prohibition'] || 0

  return (
    <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
      {[
        { label: 'Total', value: register.length, color: 'var(--text)' },
        { label: 'Showing', value: filtered.length, color: filtered.length < register.length ? 'var(--accent)' : 'var(--text)' },
        { label: 'Universal', value: universal, color: universal > 0 ? 'var(--red)' : 'var(--text-3)' },
        { label: 'Prohibitions', value: prohibitions, color: prohibitions > 0 ? 'var(--red)' : 'var(--text-3)' },
        { label: 'With deadlines', value: withDeadline, color: withDeadline > 0 ? 'var(--orange)' : 'var(--text-3)' },
      ].map(s => (
        <div key={s.label} className="card" style={{ padding: '8px 14px', flex: '1 1 90px' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.3rem', fontWeight: 300, color: s.color, marginBottom: 1 }}>
            {s.value}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            {s.label}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Obligation card ───────────────────────────────────────────────────────────

const PRIVACY_JURS_SET = new Set(['EU','GB','BR','SG','JP','AU','CA'])

function ObligationCard({ obl, expanded, onToggle, domain }) {
  const catMeta  = CATEGORY_META[obl.category]  || CATEGORY_META['Documentation']
  const univMeta = UNIVERSALITY_META[obl.universality] || UNIVERSALITY_META['Single jurisdiction']
  const CatIcon  = catMeta.icon || ListChecks

  // Determine domain tag for this obligation
  const oblJurs    = new Set(obl.jurisdictions || [])
  const hasPrivacy = [...oblJurs].some(j => PRIVACY_JURS_SET.has(j))
  const hasAI      = [...oblJurs].some(j => !PRIVACY_JURS_SET.has(j))
  const domainTag  = hasPrivacy && hasAI ? 'both' : hasPrivacy ? 'privacy' : 'ai'
  const domainColor = domainTag === 'privacy' ? '#7c9ef7' : 'var(--accent)'

  return (
    <div style={{
      background: 'var(--bg-2)',
      border: `1px solid ${obl.category === 'Prohibition' ? 'rgba(224,82,82,0.3)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
    }}>
      {/* Header row */}
      <div style={{ padding: '11px 14px', cursor: 'pointer', userSelect: 'none' }} onClick={onToggle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          {/* Category pill */}
          <span style={{
            display: 'flex', alignItems: 'center', gap: 4,
            fontSize: 10, padding: '2px 7px', borderRadius: 3, flexShrink: 0,
            background: catMeta.bg, color: catMeta.color,
            fontFamily: 'var(--font-mono)',
          }}>
            <CatIcon size={10} />
            {obl.category}
          </span>

          {/* Title */}
          <span style={{ flex: 1, fontSize: 13, fontWeight: 500, minWidth: 0 }}
            className="truncate">{obl.title}</span>

          {/* Deadline */}
          {obl.earliest_deadline && (
            <span style={{ fontSize: 10, color: 'var(--red)', fontFamily: 'var(--font-mono)', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 3 }}>
              <Clock size={10} /> {obl.earliest_deadline}
            </span>
          )}

          {/* Scope */}
          <span style={{ fontSize: 10, color: univMeta.color, fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
            {univMeta.label}
          </span>

          {/* Domain tag - only show when viewing "All" */}
          {!domain && domainTag !== 'ai' && (
            <span style={{
              fontSize: 9, padding: '1px 5px', borderRadius: 3, flexShrink: 0,
              background: domainTag === 'both' ? 'rgba(212,168,67,0.12)' : '#7c9ef720',
              color: domainTag === 'both' ? 'var(--accent)' : '#7c9ef7',
              fontFamily: 'var(--font-mono)',
            }}>
              {domainTag === 'both' ? 'AI+PRIV' : 'PRIVACY'}
            </span>
          )}

          {/* Source count */}
          <span style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
            {(obl.source_count || obl.sources?.length || 0)} src
          </span>

          {expanded
            ? <ChevronUp size={13} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
            : <ChevronDown size={13} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
          }
        </div>

        {/* Jurisdiction pills - always visible */}
        {(obl.jurisdictions?.length > 0) && (
          <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
            {obl.jurisdictions.map(j => (
              <span key={j} style={{
                fontSize: 9, padding: '1px 5px', borderRadius: 3,
                background: 'var(--bg-4)', color: 'var(--text-3)',
                fontFamily: 'var(--font-mono)',
              }}>{j}</span>
            ))}
          </div>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '14px 14px', background: 'var(--bg-3)', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Description */}
          {obl.description && (
            <p style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.65, margin: 0 }}>
              {obl.description}
            </p>
          )}

          {/* Strictest scope */}
          {obl.strictest_scope && obl.strictest_scope !== obl.description && (
            <div style={{ padding: '9px 12px', background: 'var(--bg-4)', borderRadius: 'var(--radius)', borderLeft: '3px solid var(--accent)' }}>
              <div style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', marginBottom: 4 }}>
                Strictest scope
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-2)', lineHeight: 1.5 }}>
                {obl.strictest_scope}
              </div>
            </div>
          )}

          {/* Notes */}
          {obl.notes && (
            <div style={{ fontSize: 12, color: 'var(--text-3)', fontStyle: 'italic', lineHeight: 1.5 }}>
              {obl.notes}
            </div>
          )}

          {/* Sources */}
          {(obl.sources?.length > 0) && (
            <div>
              <div style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 7 }}>
                Source Regulations ({obl.sources.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
                {obl.sources.map((s, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 12 }}>
                    <Badge level={s.jurisdiction}>{s.jurisdiction}</Badge>
                    <span style={{ flex: 1, color: 'var(--text-2)', minWidth: 0 }}>{s.regulation_title}</span>
                    {s.deadline && (
                      <span style={{ fontSize: 11, color: 'var(--red)', fontFamily: 'var(--font-mono)', flexShrink: 0 }}>
                        ⚑ {s.deadline}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Placeholder ───────────────────────────────────────────────────────────────

function RegisterPlaceholder({ onLoad, hasJurs }) {
  return (
    <div style={{ padding: '48px 40px', maxWidth: 560 }}>
      <ListChecks size={36} style={{ color: 'var(--accent)', marginBottom: 18 }} />
      <h2 style={{ fontWeight: 300, fontSize: '1.4rem', marginBottom: 14 }}>
        Consolidated Obligation Register
      </h2>
      <p style={{ fontSize: 14, color: 'var(--text-2)', lineHeight: 1.75, marginBottom: 28 }}>
        Select jurisdictions in the left panel and load the register to see every distinct
        compliance obligation - deduplicated across all overlapping regulations - with source
        citations, deadlines, and scope comparisons.
      </p>
      <p style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.65, marginBottom: 28 }}>
        <strong style={{ color: 'var(--text-2)' }}>Fast mode</strong> runs instantly from
        baseline files - no API call needed.{' '}
        <strong style={{ color: 'var(--text-2)' }}>Full mode</strong> uses Claude to
        semantically deduplicate and enrich, then caches for 24 hours.
      </p>
      <button className="btn-primary" onClick={onLoad} disabled={!hasJurs}>
        <ListChecks size={14} />
        {hasJurs ? 'Load Register' : 'Select jurisdictions first'}
      </button>
    </div>
  )
}
