import { useState, useEffect, useRef } from 'react'
import { CheckCheck, GitCompare, Filter, ChevronDown, ChevronUp, ExternalLink, Search } from 'lucide-react'
import { api } from '../api.js'
import { Badge, Spinner, EmptyState, SectionHeader, RequirementList, DomainFilter, ViewHeader } from '../components.jsx'

const SEVERITY_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 }

export default function Changes() {
  const [domain, setDomain] = useState(() => {
    try { return localStorage.getItem('aris_domain_changes') ?? null } catch { return null }
  })
  const handleDomainChange = (d) => {
    setDomain(d)
    try { localStorage.setItem('aris_domain_changes', d ?? '') } catch {}
  }
  const [changes,    setChanges]    = useState([])
  const [loading,    setLoading]    = useState(true)
  const [expanded,   setExpanded]   = useState({})
  const [severity,   setSeverity]   = useState('')
  const [diffType,   setDiffType]   = useState('')
  const [unreviewed, setUnreviewed] = useState(false)
  const [days,       setDays]       = useState(30)
  const [search,     setSearch]     = useState('')
  const [focusedIdx, setFocusedIdx] = useState(0)

  const load = async () => {
    setLoading(true)
    try {
      const data = await api.changes({ days, severity, diff_type: diffType, unreviewed, ...(domain ? { domain } : {}) })
      setChanges(data.sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4)))
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [days, severity, diffType, unreviewed])

  const review = async (id) => {
    await api.reviewChange(id)
    setChanges(prev => prev.map(c => c.id === id ? { ...c, reviewed: true } : c))
  }

  // Client-side keyword search across change summary text
  const filteredChanges = search.trim()
    ? changes.filter(c => {
        const q = search.toLowerCase()
        return (c.change_summary || '').toLowerCase().includes(q)
          || (c.base_document_id || '').toLowerCase().includes(q)
          || (c.new_document_id  || '').toLowerCase().includes(q)
          || (c.overall_assessment || '').toLowerCase().includes(q)
      })
    : changes

  const reviewAll = async () => {
    const unrev = filteredChanges.filter(c => !c.reviewed)
    await Promise.all(unrev.map(c => api.reviewChange(c.id)))
    setChanges(prev => prev.map(c => ({ ...c, reviewed: true })))
  }

  const toggle = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }))

  // Keyboard triage: J/K navigate, Space/Enter mark reviewed, E expand, U toggle unreviewed
  useEffect(() => {
    const handler = (e) => {
      // Don't fire if focus is inside an input/textarea
      if (['INPUT','TEXTAREA','SELECT'].includes(e.target.tagName)) return
      const items = filteredChanges
      if (!items.length) return
      if (e.key === 'j' || e.key === 'ArrowDown') {
        e.preventDefault()
        setFocusedIdx(i => Math.min(i + 1, items.length - 1))
      } else if (e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault()
        setFocusedIdx(i => Math.max(i - 1, 0))
      } else if ((e.key === ' ' || e.key === 'Enter') && !e.metaKey && !e.ctrlKey) {
        e.preventDefault()
        const item = items[focusedIdx]
        if (item && !item.reviewed) review(item.id)
      } else if (e.key === 'e' || e.key === 'o') {
        e.preventDefault()
        const item = items[focusedIdx]
        if (item) toggle(item.id)
      } else if (e.key === 'u') {
        e.preventDefault()
        setUnreviewed(v => !v)
      } else if (e.key === 'r' && !e.metaKey) {
        e.preventDefault()
        load()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [filteredChanges, focusedIdx])

  // Keep focusedIdx in bounds when list changes
  useEffect(() => {
    setFocusedIdx(0)
  }, [changes.length, severity, diffType, unreviewed, search])

  // Scroll focused card into view
  const listRef = useRef(null)
  useEffect(() => {
    if (!listRef.current) return
    const cards = listRef.current.querySelectorAll('[data-change-card]')
    if (cards[focusedIdx]) {
      cards[focusedIdx].scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [focusedIdx])

  const unreviewedCount = changes.filter(c => !c.reviewed).length

  return (
    <div style={{ padding: '28px 32px', maxWidth: 900 }}>
      <ViewHeader
        title="Regulatory Changes"
        subtitle={`${changes.length} changes · ${unreviewedCount} unreviewed`}
        domain={domain}
        onDomainChange={handleDomainChange}
        action={unreviewedCount > 0 && (
          <button className="btn-secondary btn-sm" onClick={reviewAll}
            title="Mark all visible changes as reviewed">
            <CheckCheck size={13}/> Mark all reviewed
          </button>
        )}
      />

      {/* Filters */}
      <div className="flex gap-3" style={{ marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: '1 1 200px', minWidth: 160 }}>
          <Search size={12} style={{ position: 'absolute', left: 9, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-3)', pointerEvents: 'none' }} />
          <input
            placeholder="Search changes…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ paddingLeft: 28, width: '100%', boxSizing: 'border-box' }}
          />
        </div>
        <select value={days} onChange={e => setDays(Number(e.target.value))} style={{ width: 110 }}>
          <option value={7}>7 days</option>
          <option value={14}>14 days</option>
          <option value={30}>30 days</option>
          <option value={90}>90 days</option>
        </select>
        <select value={severity} onChange={e => setSeverity(e.target.value)} style={{ width: 130 }}>
          <option value="">All Severities</option>
          <option>Critical</option>
          <option>High</option>
          <option>Medium</option>
          <option>Low</option>
        </select>
        <select value={diffType} onChange={e => setDiffType(e.target.value)} style={{ width: 160 }}>
          <option value="">All Change Types</option>
          <option value="version_update">Version Updates</option>
          <option value="addendum">Addenda / Amendments</option>
        </select>
        <label className="flex items-center gap-2" style={{ fontSize: 13, cursor: 'pointer', color: 'var(--text-2)' }}>
          <input
            type="checkbox"
            checked={unreviewed}
            onChange={e => setUnreviewed(e.target.checked)}
            style={{ width: 'auto', accentColor: 'var(--accent)' }}
          />
          Unreviewed only
        </label>
      </div>

      {/* Keyboard hint */}
      {!loading && filteredChanges.length > 0 && (
        <div style={{ fontSize: 11, color: 'var(--text-3)', marginBottom: 12,
          padding: '6px 12px', background: 'var(--bg-2)', borderRadius: 'var(--radius)',
          border: '1px solid var(--border)', fontFamily: 'var(--font-mono)',
          display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <span><kbd style={{background:'var(--bg-3)',padding:'1px 5px',borderRadius:3,border:'1px solid var(--border)'}}>J/K</kbd> navigate</span>
          <span><kbd style={{background:'var(--bg-3)',padding:'1px 5px',borderRadius:3,border:'1px solid var(--border)'}}>Space</kbd> mark reviewed</span>
          <span><kbd style={{background:'var(--bg-3)',padding:'1px 5px',borderRadius:3,border:'1px solid var(--border)'}}>E</kbd> expand</span>
          <span><kbd style={{background:'var(--bg-3)',padding:'1px 5px',borderRadius:3,border:'1px solid var(--border)'}}>U</kbd> unreviewed only</span>
          <span><kbd style={{background:'var(--bg-3)',padding:'1px 5px',borderRadius:3,border:'1px solid var(--border)'}}>R</kbd> reload</span>
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><Spinner size={24} /></div>
      ) : filteredChanges.length === 0 ? (
        <EmptyState
          icon={GitCompare}
          title={search ? `No changes matching "${search}"` : "No changes detected"}
          message={search
            ? "Try a different search term, or clear the search to see all changes."
            : "Changes appear automatically when a regulation is updated or an addendum is linked. Run agents to check for updates."
          }
        />
      ) : (
        <div ref={listRef} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filteredChanges.map((c, idx) => (
            <ChangeCard
              key={c.id}
              change={c}
              expanded={!!expanded[c.id]}
              focused={idx === focusedIdx}
              onToggle={() => { setFocusedIdx(idx); toggle(c.id) }}
              onReview={() => review(c.id)}
              onClick={() => setFocusedIdx(idx)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function ChangeCard({ change: c, expanded, focused, onToggle, onReview, onClick }) {
  const isVersionUpdate = c.diff_type === 'version_update'
  const borderColor = {
    Critical: 'var(--red)',
    High:     'var(--orange)',
    Medium:   'var(--yellow)',
    Low:      'var(--border)',
  }[c.severity] || 'var(--border)'

  return (
    <div
      data-change-card="1"
      onClick={onClick}
      style={{
        background: 'var(--bg-2)',
        border: `1px solid ${borderColor}`,
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
        opacity: c.reviewed ? 0.65 : 1,
        transition: 'box-shadow 0.15s',
        outline: focused ? '2px solid var(--accent)' : '2px solid transparent',
        outlineOffset: 2,
        scrollMarginTop: 12,
      }}
    >
      {/* Header */}
      <div
        style={{ padding: '14px 18px', cursor: 'pointer' }}
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          <Badge level={c.severity}>{c.severity}</Badge>
          <span style={{
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-3)',
            background: 'var(--bg-4)',
            padding: '2px 8px',
            borderRadius: 4,
          }}>
            {isVersionUpdate ? 'VERSION UPDATE' : 'ADDENDUM'}
          </span>
          {!c.reviewed && (
            <span style={{ fontSize: 11, color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>● NEW</span>
          )}
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
            {c.detected_at?.slice(0, 10)}
          </span>
          {expanded ? <ChevronUp size={14} style={{ color: 'var(--text-3)' }} /> : <ChevronDown size={14} style={{ color: 'var(--text-3)' }} />}
        </div>

        {c.doc_title && (
          <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)', marginTop: 8, lineHeight: 1.4 }}>
            {c.doc_title}
          </div>
        )}
        <p style={{ fontSize: 13, color: 'var(--text-2)', marginTop: c.doc_title ? 4 : 8, lineHeight: 1.5 }}>
          {c.change_summary}
        </p>

        {/* Doc references */}
        <div style={{ marginTop: 8, display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
          <span>BASE: {c.base_document_id?.slice(0, 50)}</span>
          <span>→</span>
          <span>NEW: {c.new_document_id?.slice(0, 50)}</span>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ borderTop: '1px solid var(--border)', padding: '16px 18px' }}>
          {/* Side-by-side diff highlights */}
          {(c.added_requirements?.length > 0 || c.removed_requirements?.length > 0 || c.modified_requirements?.length > 0) && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', color: 'var(--red)', marginBottom: 8 }}>
                  ＋ Added / Changed Requirements
                </div>
                {c.added_requirements?.map((r, i) => (
                  <div key={i} className="diff-added" style={{ padding: '6px 10px', borderRadius: 4, marginBottom: 4, fontSize: 12, lineHeight: 1.5 }}>
                    {typeof r === 'string' ? r : r.description}
                    {typeof r === 'object' && r.section && <span style={{ marginLeft: 8, opacity: 0.7 }}>[{r.section}]</span>}
                    {typeof r === 'object' && r.effective_date && <div style={{ fontSize: 11, marginTop: 2, opacity: 0.8 }}>Effective: {r.effective_date}</div>}
                  </div>
                ))}
                {c.modified_requirements?.map((r, i) => (
                  <div key={i} style={{ padding: '6px 10px', borderRadius: 4, marginBottom: 4, fontSize: 12, background: 'rgba(212,168,67,0.10)', color: 'var(--yellow)', lineHeight: 1.5 }}>
                    ~ {typeof r === 'string' ? r : r.description}
                    {typeof r === 'object' && r.direction && <span style={{ marginLeft: 8, opacity: 0.7 }}>[{r.direction}]</span>}
                  </div>
                ))}
              </div>
              <div>
                <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', color: 'var(--green)', marginBottom: 8 }}>
                  − Removed / Relaxed Requirements
                </div>
                {c.removed_requirements?.length > 0 ? c.removed_requirements.map((r, i) => (
                  <div key={i} className="diff-removed" style={{ padding: '6px 10px', borderRadius: 4, marginBottom: 4, fontSize: 12, lineHeight: 1.5 }}>
                    {typeof r === 'string' ? r : r.description}
                  </div>
                )) : (
                  <div style={{ fontSize: 12, color: 'var(--text-3)', fontStyle: 'italic' }}>No requirements removed</div>
                )}
              </div>
            </div>
          )}

          {/* Deadline changes */}
          {c.deadline_changes?.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', color: 'var(--blue)', marginBottom: 8 }}>Deadline Changes</div>
              {c.deadline_changes.map((d, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--text-2)', marginBottom: 4 }}>
                  {d.description}
                  {d.old_deadline && <span> — <span style={{ color: 'var(--red)' }}>{d.old_deadline}</span> → <span style={{ color: 'var(--green)' }}>{d.new_deadline}</span></span>}
                </div>
              ))}
            </div>
          )}

          {/* Definition changes */}
          {c.definition_changes?.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', color: 'var(--text-3)', marginBottom: 8 }}>Definition Changes</div>
              {c.definition_changes.map((d, i) => (
                <div key={i} style={{ fontSize: 12, marginBottom: 8, padding: '8px 10px', background: 'var(--bg-3)', borderRadius: 4 }}>
                  <strong style={{ color: 'var(--text)' }}>{d.term}</strong>
                  {d.old_definition && <div style={{ color: 'var(--red)', marginTop: 2 }}>Was: {d.old_definition}</div>}
                  {d.new_definition && <div style={{ color: 'var(--green)', marginTop: 2 }}>Now: {d.new_definition}</div>}
                  {d.impact && <div style={{ color: 'var(--text-3)', marginTop: 2 }}>Impact: {d.impact}</div>}
                  {d.clarification && <div style={{ color: 'var(--text-2)', marginTop: 2 }}>{d.clarification}</div>}
                </div>
              ))}
            </div>
          )}

          {/* New action items */}
          {c.new_action_items?.length > 0 && (
            <RequirementList items={c.new_action_items ?? []} label="New Action Items Required" color="var(--accent)" />
          )}

          {/* Obsolete actions */}
          {c.obsolete_action_items?.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', textTransform: 'uppercase', color: 'var(--text-3)', marginBottom: 6 }}>No Longer Required</div>
              {c.obsolete_action_items.map((a, i) => (
                <div key={i} style={{ fontSize: 12, color: 'var(--text-3)', textDecoration: 'line-through', marginBottom: 3 }}>{a}</div>
              ))}
            </div>
          )}

          {/* Assessment */}
          {c.overall_assessment && (
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, marginTop: 12, fontSize: 13, color: 'var(--text-2)', fontStyle: 'italic', lineHeight: 1.65 }}>
              {c.overall_assessment}
            </div>
          )}

          {/* Review button */}
          {!c.reviewed && (
            <div style={{ marginTop: 16 }}>
              <button className="btn-primary btn-sm" onClick={onReview}>
                <CheckCheck size={13} /> Mark as Reviewed
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
