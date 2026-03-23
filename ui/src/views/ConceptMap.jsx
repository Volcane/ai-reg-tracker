import { useState, useEffect, useCallback } from 'react'
import {
  Layers, ChevronDown, ChevronUp, RefreshCw, Sparkles,
  AlertCircle, CheckCircle2, Info, Globe, BookOpen,
} from 'lucide-react'
import { Spinner, EmptyState, SectionHeader, Badge } from '../components.jsx'
import { useNavigate } from 'react-router-dom'

// ── API ───────────────────────────────────────────────────────────────────────

const conceptApi = {
  list:  ()       => fetch('/api/concepts').then(r => r.json()),
  get:   (key)    => fetch(`/api/concepts/${key}`).then(r => r.json()),
  build: (key)    => fetch(`/api/concepts/${key}/build`, { method: 'POST' }).then(r => r.json()),
  force: (key)    => fetch(`/api/concepts/${key}?force=true`).then(r => r.json()),
}

// ── Styling ───────────────────────────────────────────────────────────────────

const STRENGTH_CONFIG = {
  mandatory: {
    color: 'var(--red)',
    bg:    'rgba(224,82,82,0.08)',
    icon:  AlertCircle,
    label: 'Mandatory',
  },
  recommended: {
    color: 'var(--yellow)',
    bg:    'rgba(212,168,67,0.08)',
    icon:  Info,
    label: 'Recommended',
  },
  guidance: {
    color: 'var(--text-3)',
    bg:    'var(--bg-3)',
    icon:  CheckCircle2,
    label: 'Guidance',
  },
}

const JUR_COLORS = {
  EU:      '#4f8fe0', Federal: '#e07c4f', PA: '#52a878',
  GB:      '#a06bd4', CA:      '#d4a843', JP: '#e05252',
  AU:      '#4fd4c8', SG:      '#d44fa0', BR: '#8fe04f',
}

// ── Entry card ────────────────────────────────────────────────────────────────

function EntryCard({ entry }) {
  const [expanded, setExpanded] = useState(false)
  const navigate   = useNavigate()
  const cfg        = STRENGTH_CONFIG[entry.strength] || STRENGTH_CONFIG.guidance
  const StrIcon    = cfg.icon
  const jurColor   = JUR_COLORS[entry.jurisdiction] || 'var(--text-3)'

  return (
    <div style={{
      border:       `1px solid var(--border)`,
      borderLeft:   `4px solid ${jurColor}`,
      borderRadius: 'var(--radius)',
      background:   'var(--bg-2)',
      marginBottom: 8,
      overflow:     'hidden',
    }}>
      {/* Header row */}
      <div
        className="flex items-center gap-3"
        style={{ padding: '11px 14px', cursor: 'pointer' }}
        onClick={() => setExpanded(e => !e)}
      >
        {/* Jurisdiction badge */}
        <div style={{
          fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 700,
          color: jurColor, minWidth: 36,
        }}>
          {entry.jurisdiction}
        </div>

        {/* Regulation name */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)' }}>
            {entry.baseline_title || entry.baseline_id}
          </div>
          {entry.section && (
            <div style={{ fontSize: 10, color: 'var(--text-3)', fontFamily: 'var(--font-mono)', marginTop: 1 }}>
              {entry.section}
            </div>
          )}
        </div>

        {/* Strength badge */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 4,
          fontSize: 10, fontFamily: 'var(--font-mono)',
          color: cfg.color, background: cfg.bg,
          padding: '3px 8px', borderRadius: 4, flexShrink: 0,
        }}>
          <StrIcon size={10} />
          {cfg.label}
        </div>

        {/* Expand toggle */}
        <div style={{ color: 'var(--text-3)', flexShrink: 0 }}>
          {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </div>
      </div>

      {/* Obligation preview (always visible) */}
      <div style={{
        padding:     '0 14px 10px 54px',
        fontSize:    12,
        color:       'var(--text-2)',
        lineHeight:  1.55,
      }}>
        {entry.obligation}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{
          borderTop:  '1px solid var(--border)',
          padding:    '12px 14px 12px 54px',
          background: 'var(--bg-3)',
          display:    'flex', flexDirection: 'column', gap: 10,
        }}>
          {entry.scope && (
            <div>
              <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-3)',
                            textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>
                Scope
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-2)' }}>{entry.scope}</div>
            </div>
          )}

          {entry.trigger && (
            <div>
              <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-3)',
                            textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>
                Trigger
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-2)' }}>{entry.trigger}</div>
            </div>
          )}

          {entry.similarity_notes && (
            <div>
              <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-3)',
                            textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 3 }}>
                Comparison
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-3)', fontStyle: 'italic',
                            lineHeight: 1.5 }}>
                {entry.similarity_notes}
              </div>
            </div>
          )}

          <button
            className="btn-ghost btn-sm"
            style={{ alignSelf: 'flex-start', marginTop: 2 }}
            onClick={() => navigate(`/ask`)}
          >
            <Sparkles size={11} style={{ color: 'var(--accent)' }} />
            Ask ARIS about {entry.baseline_title?.split(' ').slice(0,3).join(' ')}
          </button>
        </div>
      )}
    </div>
  )
}

// ── Concept picker sidebar ────────────────────────────────────────────────────

function ConceptSidebar({ concepts, selected, onSelect, loading }) {
  const mandatory_counts = concepts.reduce((acc, c) => {
    acc[c.key] = c.entry_count
    return acc
  }, {})

  return (
    <div style={{
      width:       260,
      flexShrink:  0,
      borderRight: '1px solid var(--border)',
      overflow:    'auto',
      padding:     '20px 0',
    }}>
      <div style={{
        fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-3)',
        textTransform: 'uppercase', letterSpacing: '0.06em',
        padding: '0 18px 10px',
      }}>
        Concepts
      </div>

      {loading ? (
        <div style={{ padding: '20px 18px' }}><Spinner /></div>
      ) : (
        concepts.map(c => (
          <div
            key={c.key}
            onClick={() => onSelect(c.key)}
            style={{
              padding:    '9px 18px',
              cursor:     'pointer',
              background: selected === c.key ? 'var(--bg-3)' : 'transparent',
              borderLeft: selected === c.key ? '3px solid var(--accent)' : '3px solid transparent',
              transition: 'all 0.1s',
            }}
          >
            <div style={{
              fontSize:   12,
              fontWeight: selected === c.key ? 500 : 400,
              color:      selected === c.key ? 'var(--text)' : 'var(--text-2)',
              marginBottom: 2,
            }}>
              {c.label}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {c.cached ? (
                <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)',
                               color: 'var(--green)' }}>
                   -  {c.entry_count} jurisdictions
                </span>
              ) : (
                <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)',
                               color: 'var(--text-3)' }}>
                   -  Not built
                </span>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  )
}

// ── Strength filter bar ───────────────────────────────────────────────────────

function StrengthFilter({ activeStrengths, onToggle, counts }) {
  return (
    <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
      <span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
        Filter:
      </span>
      {Object.entries(STRENGTH_CONFIG).map(([key, cfg]) => {
        const Icon   = cfg.icon
        const active = activeStrengths.has(key)
        const count  = counts[key] || 0
        return (
          <button
            key={key}
            onClick={() => onToggle(key)}
            style={{
              display:      'flex', alignItems: 'center', gap: 4,
              fontSize:     11, fontFamily: 'var(--font-mono)',
              color:        active ? cfg.color : 'var(--text-3)',
              background:   active ? cfg.bg : 'transparent',
              border:       `1px solid ${active ? cfg.color : 'var(--border)'}`,
              borderRadius: 4, padding: '3px 8px', cursor: 'pointer',
              opacity:      count === 0 ? 0.4 : 1,
            }}
          >
            <Icon size={10} />
            {cfg.label} {count > 0 && `(${count})`}
          </button>
        )
      })}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ConceptMap() {
  const [concepts,         setConcepts]        = useState([])
  const [conceptsLoading,  setConceptsLoading] = useState(true)
  const [selectedKey,      setSelectedKey]     = useState(null)
  const [conceptData,      setConceptData]     = useState(null)
  const [mapLoading,       setMapLoading]      = useState(false)
  const [building,         setBuilding]        = useState(false)
  const [activeStrengths,  setActive]          = useState(
    new Set(['mandatory', 'recommended', 'guidance'])
  )
  const [jurFilter,        setJurFilter]       = useState('')
  const navigate = useNavigate()

  // Load concept list
  useEffect(() => {
    setConceptsLoading(true)
    conceptApi.list()
      .then(d => setConcepts(d.concepts || []))
      .catch(() => {})
      .finally(() => setConceptsLoading(false))
  }, [])

  // Load concept map when selection changes
  const loadConcept = useCallback(async (key) => {
    if (!key) return
    setMapLoading(true)
    setConceptData(null)
    try {
      const data = await conceptApi.get(key)
      setConceptData(data)
    } catch (e) {
      setConceptData({ error: e.message })
    } finally {
      setMapLoading(false)
    }
  }, [])

  const selectConcept = (key) => {
    setSelectedKey(key)
    loadConcept(key)
  }

  const buildConcept = async () => {
    if (!selectedKey) return
    setBuilding(true)
    try {
      await conceptApi.build(selectedKey)
      // Poll until done (concept map is built in background)
      let attempts = 0
      const poll = setInterval(async () => {
        try {
          const data = await conceptApi.get(selectedKey)
          if (data.entry_count > 0 || ++attempts > 30) {
            clearInterval(poll)
            setBuilding(false)
            setConceptData(data)
            // Refresh concept list to update cache indicators
            const list = await conceptApi.list()
            setConcepts(list.concepts || [])
          }
        } catch {
          clearInterval(poll)
          setBuilding(false)
        }
      }, 2000)
    } catch {
      setBuilding(false)
    }
  }

  const toggleStrength = (s) => {
    setActive(prev => {
      const next = new Set(prev)
      if (next.has(s)) next.delete(s)
      else next.add(s)
      return next
    })
  }

  // Filter entries
  const entries       = conceptData?.entries || []
  const filteredEntries = entries.filter(e => {
    if (!activeStrengths.has(e.strength)) return false
    if (jurFilter && e.jurisdiction !== jurFilter) return false
    return true
  })

  // Count by strength
  const strengthCounts = entries.reduce((acc, e) => {
    acc[e.strength] = (acc[e.strength] || 0) + 1
    return acc
  }, {})

  // Unique jurisdictions in this map
  const jurisdictions = [...new Set(entries.map(e => e.jurisdiction))].sort()
  const selectedConcept = concepts.find(c => c.key === selectedKey)
  const isCached = selectedConcept?.cached

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── Concept sidebar ── */}
      <ConceptSidebar
        concepts={concepts}
        selected={selectedKey}
        onSelect={selectConcept}
        loading={conceptsLoading}
      />

      {/* ── Main content ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
          {selectedConcept ? (
            <>
              <div className="flex items-center justify-between" style={{ marginBottom: 4 }}>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 300 }}>
                    {selectedConcept.label}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 3,
                                lineHeight: 1.5, maxWidth: 600 }}>
                    {conceptData?.description || selectedConcept.description}
                  </div>
                </div>
                <div className="flex gap-2">
                  {isCached && (
                    <button
                      className="btn-ghost btn-sm"
                      onClick={buildConcept}
                      disabled={building || mapLoading}
                      title="Rebuild with fresh LLM analysis"
                    >
                      <RefreshCw size={12} style={{
                        animation: building ? 'spin 1s linear infinite' : 'none'
                      }} />
                      Refresh
                    </button>
                  )}
                  {!isCached && (
                    <button
                      className="btn-primary btn-sm"
                      onClick={buildConcept}
                      disabled={building || mapLoading}
                    >
                      {building ? (
                        <><Spinner size={12} /> Building…</>
                      ) : (
                        <><Layers size={12} /> Build Map</>
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Filter bar */}
              {entries.length > 0 && (
                <div className="flex items-center gap-3"
                     style={{ paddingTop: 12, paddingBottom: 12,
                              borderBottom: '1px solid var(--border)',
                              flexWrap: 'wrap' }}>
                  <StrengthFilter
                    activeStrengths={activeStrengths}
                    onToggle={toggleStrength}
                    counts={strengthCounts}
                  />
                  {jurisdictions.length > 1 && (
                    <>
                      <div style={{ width: 1, height: 16, background: 'var(--border)' }} />
                      <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
                        <Globe size={11} style={{ color: 'var(--text-3)' }} />
                        {['', ...jurisdictions].map(j => (
                          <button
                            key={j || 'all'}
                            className={jurFilter === j ? 'btn-primary btn-sm' : 'btn-ghost btn-sm'}
                            style={{ fontSize: 11, padding: '3px 10px' }}
                            onClick={() => setJurFilter(j)}
                          >
                            {j || 'All'}
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                  <div style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-3)',
                                fontFamily: 'var(--font-mono)' }}>
                    {filteredEntries.length} of {entries.length} jurisdictions
                  </div>
                </div>
              )}
            </>
          ) : (
            <SectionHeader
              title="Concept Map"
              subtitle="Cross-jurisdiction comparison of regulatory concepts"
            />
          )}
        </div>

        {/* Content area */}
        <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px' }}>
          {!selectedKey ? (
            <div style={{ maxWidth: 540, margin: '40px auto', textAlign: 'center' }}>
              <div style={{
                width: 56, height: 56, borderRadius: '50%',
                background: 'var(--bg-3)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 20px',
              }}>
                <Layers size={24} style={{ color: 'var(--accent)' }} />
              </div>
              <div style={{ fontSize: 16, fontWeight: 300, marginBottom: 8 }}>
                Select a concept
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.6 }}>
                Choose a regulatory concept from the sidebar to see how every
                jurisdiction in your corpus addresses it - with specific obligations,
                scope, triggers, and cross-jurisdiction comparisons.
              </div>
            </div>
          ) : mapLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center',
                          height: 200, gap: 12, color: 'var(--text-3)', fontSize: 13 }}>
              <Spinner /> Loading concept map…
            </div>
          ) : conceptData?.error ? (
            <div style={{ color: 'var(--red)', fontSize: 13, padding: 20 }}>
              Error: {conceptData.error}
            </div>
          ) : entries.length === 0 ? (
            <div style={{ padding: '40px 0', textAlign: 'center' }}>
              <EmptyState
                icon={BookOpen}
                title="No concept map yet"
                message={`Click "Build Map" to generate a cross-jurisdiction analysis of "${selectedConcept?.label}". This uses one LLM call and the result is cached for 7 days.`}
              />
            </div>
          ) : filteredEntries.length === 0 ? (
            <div style={{ padding: '20px 0', color: 'var(--text-3)', fontSize: 13,
                          textAlign: 'center' }}>
              No entries match the current filters.
            </div>
          ) : (
            <div style={{ maxWidth: 860 }}>
              {/* Summary stats */}
              <div className="flex gap-4" style={{ marginBottom: 16, flexWrap: 'wrap' }}>
                {Object.entries(STRENGTH_CONFIG).map(([key, cfg]) => {
                  const count = strengthCounts[key] || 0
                  if (!count) return null
                  const Icon = cfg.icon
                  return (
                    <div key={key} style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      fontSize: 12, color: cfg.color,
                    }}>
                      <Icon size={12} />
                      {count} {cfg.label.toLowerCase()}
                    </div>
                  )
                })}
                {conceptData?.built_at && (
                  <div style={{ marginLeft: 'auto', fontSize: 11, fontFamily: 'var(--font-mono)',
                                color: 'var(--text-3)' }}>
                    Built {new Date(conceptData.built_at).toLocaleDateString()}
                  </div>
                )}
              </div>

              {/* Entry cards */}
              {filteredEntries.map((entry, i) => (
                <EntryCard key={`${entry.baseline_id}-${i}`} entry={entry} />
              ))}

              {/* Ask ARIS prompt */}
              <div style={{
                marginTop: 24, padding: '14px 18px',
                background: 'var(--bg-3)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                display: 'flex', alignItems: 'center', gap: 12,
              }}>
                <Sparkles size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 3 }}>
                    Dig deeper with Ask ARIS
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
                    Ask follow-up questions about {selectedConcept?.label?.toLowerCase()} across jurisdictions.
                  </div>
                </div>
                <button
                  className="btn-secondary btn-sm"
                  onClick={() => navigate('/ask')}
                >
                  Open Ask ARIS →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
